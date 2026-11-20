/*
    FILE: kinematics.c
    DESC: Integracao cinematica discreta do robo diferencial
    AUTHOR: José Dercy Vieira da Silva Filho
    EMAIL: josedercysilva@gmail.com
    DATE: Out, 2026
    LICENSE: MIT
*/

#include "kinematics.h"
#include <math.h>
#include <stddef.h>
#include <stdio.h>

#define MAX_VALID_DT_SEC (1.0)

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

bool kinematics_init_state(robot_state_t *p_state) {
    if (!c_assert(p_state != NULL)) {
        return false;
    }

    p_state->xc = 0.0;
    p_state->yc = 0.0;
    p_state->theta = 0.0;

    return true;
}

bool kinematics_compute_control(
    double time_sec,
    control_input_t *p_control
) {
    if (!c_assert(p_control != NULL)) {
        return false;
    }

    if (time_sec < 0.0) {
        p_control->v = 0.0;
        p_control->omega = 0.0;
    } else if (time_sec < SIM_SWITCH_TIME_SEC) {
        p_control->v = CONTROL_LINEAR_VEL_MPS;
        p_control->omega = -CONTROL_ANGULAR_VEL_RADPS;
    } else {
        p_control->v = CONTROL_LINEAR_VEL_MPS;
        p_control->omega = CONTROL_ANGULAR_VEL_RADPS;
    }

    return true;
}

bool kinematics_compute_front_pose(
    const robot_state_t *p_state,
    robot_pose_t *p_pose
) {
    if (!c_assert(p_state != NULL)) {
        return false;
    }
    if (!c_assert(p_pose != NULL)) {
        return false;
    }

    const double radius_m = 0.5 * ROBOT_DIAMETER_M;
    const double cos_theta = cos(p_state->theta);
    const double sin_theta = sin(p_state->theta);

    p_pose->x = p_state->xc + (radius_m * cos_theta);
    p_pose->y = p_state->yc + (radius_m * sin_theta);
    p_pose->theta = p_state->theta;

    return true;
}

bool kinematics_step(
    robot_state_t *p_state,
    const control_input_t *p_control,
    double dt_sec,
    robot_pose_t *p_pose
) {
    if (!c_assert(p_state != NULL)) {
        return false;
    }
    if (!c_assert(p_control != NULL)) {
        return false;
    }
    if (!c_assert(p_pose != NULL)) {
        return false;
    }
    if (!c_assert((dt_sec > 0.0) && (dt_sec <= MAX_VALID_DT_SEC))) {
        return false;
    }

    /*
     * Equacoes de estado (Equacao 1 do roteiro):
     *   dx1/dt = sin(x3) * v
     *   dx2/dt = cos(x3) * v
     *   dx3/dt = omega
     */
    const double heading_rad = p_state->theta;
    const double dx_dt = sin(heading_rad) * p_control->v;
    const double dy_dt = cos(heading_rad) * p_control->v;
    const double dtheta_dt = p_control->omega;

    p_state->xc += dx_dt * dt_sec;
    p_state->yc += dy_dt * dt_sec;
    p_state->theta += dtheta_dt * dt_sec;

    const bool pose_ok = kinematics_compute_front_pose(p_state, p_pose);
    if (!c_assert(pose_ok)) {
        return false;
    }

    return true;
}
