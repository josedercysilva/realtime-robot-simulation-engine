/*
    FILE: rt_timer.h
    DESC: Interface de temporizacao periodica e estatisticas de jitter
    AUTHOR: José Dercy Vieira da Silva Filho
    EMAIL: josedercysilva@gmail.com
    DATE: Out, 2026
    LICENSE: MIT
*/

#ifndef RT_TIMER_H
#define RT_TIMER_H

#include <stdbool.h>
#include <stdint.h>
#include <time.h>

#define RT_NSEC_PER_SEC (1000000000ULL)
#define RT_NSEC_PER_MSEC (1000000ULL)
#define RT_MSEC_PER_SEC (1000.0)

typedef struct {
    uint32_t count;
    double mean_ms;
    double m2_ms2;
    double variance_ms2;
    double std_dev_ms;
    double min_ms;
    double max_ms;
} rt_stats_t;

typedef struct {
    struct timespec start_time;
    struct timespec next_wakeup;
    struct timespec last_wakeup;
    uint32_t period_ms;
    double elapsed_sec;
    double last_period_ms;
    double last_jitter_ms;
    rt_stats_t period_stats;
    rt_stats_t jitter_stats;
    bool is_initialized;
} rt_timer_t;

bool rt_timer_now(struct timespec *p_now);

bool rt_timer_init(
    rt_timer_t *p_timer,
    uint32_t period_ms,
    const struct timespec *p_origin
);

bool rt_timer_wait_next(rt_timer_t *p_timer);

bool rt_timer_get_elapsed_sec(
    const rt_timer_t *p_timer,
    double *p_elapsed_sec
);

#endif /* RT_TIMER_H */
