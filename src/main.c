/*
    FILE: main.c
    DESC: Ponto de entrada da simulacao multi-taxa em tempo real do robo movil
    AUTHOR: José Dercy Vieira da Silva Filho
    EMAIL: josedercysilva@gmail.com
    DATE: Out, 2026
    LICENSE: MIT
*/

#define _POSIX_C_SOURCE 200809L

#include <pthread.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include "kinematics.h"
#include "rt_timer.h"
#include "shared_mem.h"

#define PILOT_PERIOD_MS (30u)
#define PHYSICS_PERIOD_MS (50u)
#define PILOT_MAX_STEPS (668u)
#define PHYSICS_MAX_STEPS (400u)
#define LOG_BUFFER_SIZE (65536u)
#define SIMULATION_LOG_PATH ("data/simulation_log.txt")

typedef struct {
    rt_timer_t timer;
    FILE *p_log_file;
    bool status_ok;
} thread_context_t;

static char g_log_io_buffer[LOG_BUFFER_SIZE];
static thread_context_t g_pilot_ctx;
static thread_context_t g_physics_ctx;

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

static bool write_telemetry_line(
    FILE *p_file,
    double t_sec,
    const control_input_t *p_u,
    const robot_pose_t *p_yf
) {
    if ((!c_assert(p_file != NULL)) ||
        (!c_assert(p_u != NULL)) ||
        (!c_assert(p_yf != NULL))) {
        return false;
    }

    const int32_t chars_written = (int32_t)fprintf(
        p_file,
        "%.6f\t%.6f\t%.6f\t%.6f\t%.6f\t%.6f\n",
        t_sec,
        p_u->v,
        p_u->omega,
        p_yf->x,
        p_yf->y,
        p_yf->theta
    );

    return c_assert(chars_written > (int32_t)0);
}

/* Thread 1: Piloto e Telemetria (periodo: 30 ms) */
static void *pilot_telemetry_thread(void *p_arg) {
    if (!c_assert(p_arg != NULL)) {
        return NULL;
    }

    thread_context_t *p_ctx = (thread_context_t *)p_arg;
    p_ctx->status_ok = false;

    control_input_t u_cmd = { 0.0, 0.0 };
    robot_pose_t yf_pose = { 0.0, 0.0, 0.0 };

    /* Amostra inicial em t = 0.0 s */
    bool ok = kinematics_compute_control(0.0, &u_cmd);
    if (!c_assert(ok)) {
        return NULL;
    }
    ok = shared_mem_write_u(&u_cmd);
    if (!c_assert(ok)) {
        return NULL;
    }
    ok = shared_mem_read_yf(&yf_pose);
    if (!c_assert(ok)) {
        return NULL;
    }
    ok = write_telemetry_line(p_ctx->p_log_file, 0.0, &u_cmd, &yf_pose);
    if (!c_assert(ok)) {
        return NULL;
    }

    uint32_t step = 0u;
    for (step = 1u; step < PILOT_MAX_STEPS; step++) {
        ok = rt_timer_wait_next(&p_ctx->timer);
        if (!c_assert(ok)) {
            return NULL;
        }

        double t_sec = 0.0;
        ok = rt_timer_get_elapsed_sec(&p_ctx->timer, &t_sec);
        if (!c_assert(ok)) {
            return NULL;
        }

        ok = kinematics_compute_control(t_sec, &u_cmd);
        if (!c_assert(ok)) {
            return NULL;
        }

        ok = shared_mem_write_u(&u_cmd);
        if (!c_assert(ok)) {
            return NULL;
        }

        ok = shared_mem_read_yf(&yf_pose);
        if (!c_assert(ok)) {
            return NULL;
        }

        ok = write_telemetry_line(p_ctx->p_log_file, t_sec, &u_cmd, &yf_pose);
        if (!c_assert(ok)) {
            return NULL;
        }
    }

    p_ctx->status_ok = true;
    return NULL;
}

/* Thread 2: Motor de Fisica (periodo: 50 ms) */
static void *physics_engine_thread(void *p_arg) {
    if (!c_assert(p_arg != NULL)) {
        return NULL;
    }

    thread_context_t *p_ctx = (thread_context_t *)p_arg;
    p_ctx->status_ok = false;

    robot_state_t state;
    bool ok = kinematics_init_state(&state);
    if (!c_assert(ok)) {
        return NULL;
    }

    control_input_t u_cmd = { 0.0, 0.0 };
    robot_pose_t yf_pose = { 0.0, 0.0, 0.0 };

    uint32_t step = 0u;
    for (step = 0u; step < PHYSICS_MAX_STEPS; step++) {
        ok = rt_timer_wait_next(&p_ctx->timer);
        if (!c_assert(ok)) {
            return NULL;
        }

        ok = shared_mem_read_u(&u_cmd);
        if (!c_assert(ok)) {
            return NULL;
        }

        ok = kinematics_step(&state, &u_cmd, PHYSICS_DT_SEC, &yf_pose);
        if (!c_assert(ok)) {
            return NULL;
        }

        ok = shared_mem_write_yf(&yf_pose);
        if (!c_assert(ok)) {
            return NULL;
        }
    }

    p_ctx->status_ok = true;
    return NULL;
}

static void print_timing_report(
    const char *p_name,
    const rt_timer_t *p_timer
) {
    if ((p_name == NULL) || (p_timer == NULL)) {
        return;
    }

    (void)printf("\n--- %s (Nominal Period: %u ms, Samples: %u) ---\n",
                 p_name,
                 p_timer->period_ms,
                 p_timer->period_stats.count);
    (void)printf(
        "  T(k) [ms] -> Mean: %8.4f | Var: %10.6f | Std: %8.4f"
        " | Min: %8.4f | Max: %8.4f\n",
        p_timer->period_stats.mean_ms,
        p_timer->period_stats.variance_ms2,
        p_timer->period_stats.std_dev_ms,
        p_timer->period_stats.min_ms,
        p_timer->period_stats.max_ms
    );
    (void)printf(
        "  J(k) [ms] -> Mean: %+8.4f | Var: %10.6f | Std: %8.4f"
        " | Min: %+8.4f | Max: %+8.4f\n",
        p_timer->jitter_stats.mean_ms,
        p_timer->jitter_stats.variance_ms2,
        p_timer->jitter_stats.std_dev_ms,
        p_timer->jitter_stats.min_ms,
        p_timer->jitter_stats.max_ms
    );
}

int32_t main(void) {
    (void)printf("=== Lab 2: Real-Time Differential Robot Simulation ===\n");
    (void)printf("Horizon: %.1f s | Thread 1: %u ms | Thread 2: %u ms\n",
                 SIM_HORIZON_SEC,
                 PILOT_PERIOD_MS,
                 PHYSICS_PERIOD_MS);

    if (!shared_mem_init()) {
        return (int32_t)1;
    }

    FILE *p_log = fopen(SIMULATION_LOG_PATH, "w");
    if (!c_assert(p_log != NULL)) {
        (void)shared_mem_destroy();
        return (int32_t)1;
    }

    const int32_t buf_rc = (int32_t)setvbuf(
        p_log,
        g_log_io_buffer,
        _IOFBF,
        sizeof(g_log_io_buffer)
    );
    if (!c_assert(buf_rc == (int32_t)0)) {
        (void)fclose(p_log);
        (void)shared_mem_destroy();
        return (int32_t)1;
    }

    struct timespec origin_time;
    if (!rt_timer_now(&origin_time)) {
        (void)fclose(p_log);
        (void)shared_mem_destroy();
        return (int32_t)1;
    }

    g_pilot_ctx.p_log_file = p_log;
    g_pilot_ctx.status_ok = false;
    g_physics_ctx.p_log_file = NULL;
    g_physics_ctx.status_ok = false;

    const bool t1_ok = rt_timer_init(
        &g_pilot_ctx.timer,
        PILOT_PERIOD_MS,
        &origin_time
    );
    const bool t2_ok = rt_timer_init(
        &g_physics_ctx.timer,
        PHYSICS_PERIOD_MS,
        &origin_time
    );
    if ((!c_assert(t1_ok)) || (!c_assert(t2_ok))) {
        (void)fclose(p_log);
        (void)shared_mem_destroy();
        return (int32_t)1;
    }

    pthread_t pilot_tid;
    pthread_t physics_tid;

    int32_t rc = (int32_t)pthread_create(
        &physics_tid,
        NULL,
        physics_engine_thread,
        &g_physics_ctx
    );
    if (!c_assert(rc == (int32_t)0)) {
        (void)fclose(p_log);
        (void)shared_mem_destroy();
        return (int32_t)1;
    }

    rc = (int32_t)pthread_create(
        &pilot_tid,
        NULL,
        pilot_telemetry_thread,
        &g_pilot_ctx
    );
    if (!c_assert(rc == (int32_t)0)) {
        (void)pthread_join(physics_tid, NULL);
        (void)fclose(p_log);
        (void)shared_mem_destroy();
        return (int32_t)1;
    }

    const int32_t join1_rc = (int32_t)pthread_join(pilot_tid, NULL);
    const int32_t join2_rc = (int32_t)pthread_join(physics_tid, NULL);

    const int32_t flush_rc = (int32_t)fflush(p_log);
    const int32_t close_rc = (int32_t)fclose(p_log);
    const bool destroy_ok = shared_mem_destroy();

    if ((!c_assert(join1_rc == (int32_t)0)) ||
        (!c_assert(join2_rc == (int32_t)0)) ||
        (!c_assert(flush_rc == (int32_t)0)) ||
        (!c_assert(close_rc == (int32_t)0)) ||
        (!c_assert(destroy_ok)) ||
        (!c_assert(g_pilot_ctx.status_ok)) ||
        (!c_assert(g_physics_ctx.status_ok))) {
        return (int32_t)1;
    }

    print_timing_report("Thread 1 (Pilot / Telemetry)", &g_pilot_ctx.timer);
    print_timing_report("Thread 2 (Physics Engine)", &g_physics_ctx.timer);
    (void)printf("\nTelemetry saved to: %s\n", SIMULATION_LOG_PATH);

    return (int32_t)0;
}
