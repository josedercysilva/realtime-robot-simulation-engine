/*
    FILE: shared_mem.c
    DESC: Memoria compartilhada protegida por mutex com heranca de prioridade
    AUTHOR: José Dercy Vieira da Silva Filho
    EMAIL: josedercysilva@gmail.com
    DATE: Out, 2026
    LICENSE: MIT
*/

#define _POSIX_C_SOURCE 200809L

#include "shared_mem.h"
#include <pthread.h>
#include <stddef.h>
#include <stdio.h>

typedef struct {
    control_input_t u;
    robot_pose_t yf;
    pthread_mutex_t mutex;
    bool is_initialized;
} shared_buffer_t;

static shared_buffer_t g_shared_buffer = {
    .u = { 0.0, 0.0 },
    .yf = { 0.0, 0.0, 0.0 },
    .is_initialized = false
};

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

bool shared_mem_init(void) 
{
    if (g_shared_buffer.is_initialized) {
        return true;
    }

    pthread_mutexattr_t attr;
    int32_t rc = (int32_t)pthread_mutexattr_init(&attr);
    if (!c_assert(rc == (int32_t)0)) {
        return false;
    }

    rc = (int32_t)pthread_mutexattr_setprotocol(&attr, PTHREAD_PRIO_INHERIT);
    if (!c_assert(rc == (int32_t)0)) {
        (void)pthread_mutexattr_destroy(&attr);
        return false;
    }

    rc = (int32_t)pthread_mutex_init(&g_shared_buffer.mutex, &attr);
    const int32_t destroy_rc = (int32_t)pthread_mutexattr_destroy(&attr);
    if ((!c_assert(rc == (int32_t)0)) ||
        (!c_assert(destroy_rc == (int32_t)0))) {
        return false;
    }

    robot_state_t init_state;
    const bool state_ok = kinematics_init_state(&init_state);
    const bool pose_ok = kinematics_compute_front_pose(
        &init_state,
        &g_shared_buffer.yf
    );
    if ((!c_assert(state_ok)) || (!c_assert(pose_ok))) {
        (void)pthread_mutex_destroy(&g_shared_buffer.mutex);
        return false;
    }

    g_shared_buffer.u.v = 0.0;
    g_shared_buffer.u.omega = 0.0;
    g_shared_buffer.is_initialized = true;

    return true;
}

bool shared_mem_destroy(void) 
{
    if (!c_assert(g_shared_buffer.is_initialized)) {
        return false;
    }

    const int32_t rc = (int32_t)pthread_mutex_destroy(&g_shared_buffer.mutex);
    if (!c_assert(rc == (int32_t)0)) {
        return false;
    }

    g_shared_buffer.is_initialized = false;
    return true;
}

bool shared_mem_write_u(const control_input_t *p_u) 
{
    if (!c_assert(p_u != NULL)) {
        return false;
    }
    if (!c_assert(g_shared_buffer.is_initialized)) {
        return false;
    }

    int32_t rc = (int32_t)pthread_mutex_lock(&g_shared_buffer.mutex);
    if (!c_assert(rc == (int32_t)0)) {
        return false;
    }

    g_shared_buffer.u.v = p_u->v;
    g_shared_buffer.u.omega = p_u->omega;

    rc = (int32_t)pthread_mutex_unlock(&g_shared_buffer.mutex);
    if (!c_assert(rc == (int32_t)0)) {
        return false;
    }

    return true;
}

bool shared_mem_read_u(control_input_t *p_u) 
{
    if (!c_assert(p_u != NULL)) {
        return false;
    }
    if (!c_assert(g_shared_buffer.is_initialized)) {
        return false;
    }

    int32_t rc = (int32_t)pthread_mutex_lock(&g_shared_buffer.mutex);
    if (!c_assert(rc == (int32_t)0)) {
        return false;
    }

    p_u->v = g_shared_buffer.u.v;
    p_u->omega = g_shared_buffer.u.omega;

    rc = (int32_t)pthread_mutex_unlock(&g_shared_buffer.mutex);
    if (!c_assert(rc == (int32_t)0)) {
        return false;
    }

    return true;
}

bool shared_mem_write_yf(const robot_pose_t *p_yf) 
{
    if (!c_assert(p_yf != NULL)) {
        return false;
    }
    if (!c_assert(g_shared_buffer.is_initialized)) {
        return false;
    }

    int32_t rc = (int32_t)pthread_mutex_lock(&g_shared_buffer.mutex);
    if (!c_assert(rc == (int32_t)0)) {
        return false;
    }

    g_shared_buffer.yf.x = p_yf->x;
    g_shared_buffer.yf.y = p_yf->y;
    g_shared_buffer.yf.theta = p_yf->theta;

    rc = (int32_t)pthread_mutex_unlock(&g_shared_buffer.mutex);
    if (!c_assert(rc == (int32_t)0)) {
        return false;
    }

    return true;
}

bool shared_mem_read_yf(robot_pose_t *p_yf) 
{
    if (!c_assert(p_yf != NULL)) {
        return false;
    }
    if (!c_assert(g_shared_buffer.is_initialized)) {
        return false;
    }

    int32_t rc = (int32_t)pthread_mutex_lock(&g_shared_buffer.mutex);
    if (!c_assert(rc == (int32_t)0)) {
        return false;
    }

    p_yf->x = g_shared_buffer.yf.x;
    p_yf->y = g_shared_buffer.yf.y;
    p_yf->theta = g_shared_buffer.yf.theta;

    rc = (int32_t)pthread_mutex_unlock(&g_shared_buffer.mutex);
    if (!c_assert(rc == (int32_t)0)) {
        return false;
    }

    return true;
}
