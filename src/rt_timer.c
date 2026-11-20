/*
    FILE: rt_timer.c
    DESC: Temporizacao periodica em tempo real e metricas estatisticas de jitter
    AUTHOR: José Dercy Vieira da Silva Filho
    EMAIL: josedercysilva@gmail.com
    DATE: Out, 2026
    LICENSE: MIT
*/

#define _POSIX_C_SOURCE 200809L

#include "rt_timer.h"
#include <errno.h>
#include <math.h>
#include <stddef.h>
#include <stdio.h>

#define MAX_NANOSLEEP_RETRIES (16u)
#define MAX_PERIOD_MS (10000u)

static void log_assertion_failure(
    const char *p_file,
    int32_t line,
    const char *p_expr
) {
    if ((p_file != NULL) && (p_expr != NULL)) {
        (void)fprintf(
            stderr,
            "[ASSERT FAIL] %s:%d: (%s)\n",
            p_file,
            line,
            p_expr
        );
    }
}

#define c_assert(e) \
    ((e) ? (true) : (log_assertion_failure(__FILE__, __LINE__, #e), false))

static void stats_reset(rt_stats_t *p_stats)
{
    if (p_stats != NULL) {
        p_stats->count = 0u;
        p_stats->mean_ms = 0.0;
        p_stats->m2_ms2 = 0.0;
        p_stats->variance_ms2 = 0.0;
        p_stats->std_dev_ms = 0.0;
        p_stats->min_ms = 0.0;
        p_stats->max_ms = 0.0;
    }
}

/* Algoritmo de Welford para atualizacao de media e variancia */
static void stats_update(rt_stats_t *p_stats, double sample_ms)
{
    if (p_stats == NULL) {
        return;
    }

    p_stats->count++;
    if (p_stats->count == 1u) {
        p_stats->mean_ms = sample_ms;
        p_stats->m2_ms2 = 0.0;
        p_stats->variance_ms2 = 0.0;
        p_stats->std_dev_ms = 0.0;
        p_stats->min_ms = sample_ms;
        p_stats->max_ms = sample_ms;
        return;
    }

    if (sample_ms < p_stats->min_ms) {
        p_stats->min_ms = sample_ms;
    }
    if (sample_ms > p_stats->max_ms) {
        p_stats->max_ms = sample_ms;
    }

    const double delta = sample_ms - p_stats->mean_ms;
    p_stats->mean_ms += delta / (double)p_stats->count;
    const double delta2 = sample_ms - p_stats->mean_ms;
    p_stats->m2_ms2 += delta * delta2;

    p_stats->variance_ms2 =
        p_stats->m2_ms2 / (double)(p_stats->count - 1u);
    if (p_stats->variance_ms2 > 0.0) {
        p_stats->std_dev_ms = sqrt(p_stats->variance_ms2);
    } else {
        p_stats->std_dev_ms = 0.0;
    }
}

static double timespec_diff_sec(
    const struct timespec *p_end,
    const struct timespec *p_start
) {
    if ((p_end == NULL) || (p_start == NULL)) {
        return 0.0;
    }

    const int64_t sec_diff =
        (int64_t)p_end->tv_sec - (int64_t)p_start->tv_sec;
    const int64_t nsec_diff =
        (int64_t)p_end->tv_nsec - (int64_t)p_start->tv_nsec;

    return (double)sec_diff +
           ((double)nsec_diff / (double)RT_NSEC_PER_SEC);
}

static void timespec_add_ms(struct timespec *p_ts, uint32_t add_ms)
{
    if (p_ts == NULL) {
        return;
    }

    const uint64_t add_sec = (uint64_t)(add_ms / 1000u);
    const uint64_t rem_ms = (uint64_t)(add_ms % 1000u);
    const uint64_t total_nsec =
        (uint64_t)p_ts->tv_nsec + (rem_ms * RT_NSEC_PER_MSEC);

    p_ts->tv_sec += (time_t)(add_sec + (total_nsec / RT_NSEC_PER_SEC));
    p_ts->tv_nsec = (int64_t)(total_nsec % RT_NSEC_PER_SEC);
}

bool rt_timer_now(struct timespec *p_now)
{
    if (!c_assert(p_now != NULL)) {
        return false;
    }

    const int32_t rc = (int32_t)clock_gettime(CLOCK_MONOTONIC, p_now);
    if (!c_assert(rc == (int32_t)0)) {
        return false;
    }

    return true;
}

bool rt_timer_init(
    rt_timer_t *p_timer,
    uint32_t period_ms,
    const struct timespec *p_origin
) {
    if (!c_assert(p_timer != NULL)) {
        return false;
    }
    if (!c_assert((period_ms > 0u) && (period_ms <= MAX_PERIOD_MS))) {
        return false;
    }

    struct timespec origin_ts;
    if (p_origin != NULL) {
        origin_ts = *p_origin;
    } else {
        const bool now_ok = rt_timer_now(&origin_ts);
        if (!c_assert(now_ok)) {
            return false;
        }
    }

    p_timer->start_time = origin_ts;
    p_timer->next_wakeup = origin_ts;
    p_timer->last_wakeup = origin_ts;
    p_timer->period_ms = period_ms;
    p_timer->elapsed_sec = 0.0;
    p_timer->last_period_ms = (double)period_ms;
    p_timer->last_jitter_ms = 0.0;
    stats_reset(&p_timer->period_stats);
    stats_reset(&p_timer->jitter_stats);
    p_timer->is_initialized = true;

    return true;
}

bool rt_timer_wait_next(rt_timer_t *p_timer)
{
    if (!c_assert(p_timer != NULL)) {
        return false;
    }
    if (!c_assert(p_timer->is_initialized)) {
        return false;
    }

    timespec_add_ms(&p_timer->next_wakeup, p_timer->period_ms);

    int32_t sleep_rc = (int32_t)EINTR;
    uint32_t retry = 0u;
    for (retry = 0u; retry < MAX_NANOSLEEP_RETRIES; retry++) {
        sleep_rc = (int32_t)clock_nanosleep(
            CLOCK_MONOTONIC,
            TIMER_ABSTIME,
            &p_timer->next_wakeup,
            NULL
        );
        if (sleep_rc != (int32_t)EINTR) {
            break;
        }
    }

    if (!c_assert(sleep_rc == (int32_t)0)) {
        return false;
    }

    struct timespec wakeup_now;
    const bool now_ok = rt_timer_now(&wakeup_now);
    if (!c_assert(now_ok)) {
        return false;
    }

    p_timer->elapsed_sec = timespec_diff_sec(
        &wakeup_now,
        &p_timer->start_time
    );
    p_timer->last_period_ms =
        timespec_diff_sec(&wakeup_now, &p_timer->last_wakeup) *
        RT_MSEC_PER_SEC;
    p_timer->last_jitter_ms =
        p_timer->last_period_ms - (double)p_timer->period_ms;
    p_timer->last_wakeup = wakeup_now;

    stats_update(&p_timer->period_stats, p_timer->last_period_ms);
    stats_update(&p_timer->jitter_stats, p_timer->last_jitter_ms);

    return true;
}

bool rt_timer_get_elapsed_sec(
    const rt_timer_t *p_timer,
    double *p_elapsed_sec
) {
    if (!c_assert(p_timer != NULL)) {
        return false;
    }
    if (!c_assert(p_elapsed_sec != NULL)) {
        return false;
    }
    if (!c_assert(p_timer->is_initialized)) {
        return false;
    }

    *p_elapsed_sec = p_timer->elapsed_sec;
    return true;
}
