/*
    FILE: kinematics.h
    DESC: Interface da cinematica discreta do robo diferencial
    AUTHOR: José Dercy Vieira da Silva Filho
    EMAIL: josedercysilva@gmail.com
    DATE: Out, 2026
    LICENSE: MIT
*/

#ifndef KINEMATICS_H
#define KINEMATICS_H

#include <stdbool.h>
#include <stdint.h>

#define KINEMATICS_PI (3.14159265358979323846)
#define ROBOT_DIAMETER_M (0.30)
#define ROBOT_RADIUS_M (0.15)
#define PHYSICS_DT_SEC (0.05)
#define SIM_HORIZON_SEC (20.0)
#define SIM_SWITCH_TIME_SEC (10.0)
#define CONTROL_LINEAR_VEL_MPS (1.0)
#define CONTROL_ANGULAR_VEL_RADPS (0.2 * KINEMATICS_PI)

/* Vetor de controle u(t) = [v, omega]^T */
typedef struct {
    double v;
    double omega;
} control_input_t;

/* Estado do centro de massa x(t) = [xc, yc, theta]^T */
typedef struct {
    double xc;
    double yc;
    double theta;
} robot_state_t;

/* Postura do ponto frontal yf(t) = [x, y, theta]^T */
typedef struct {
    double x;
    double y;
    double theta;
} robot_pose_t;

bool kinematics_init_state(robot_state_t *p_state);

bool kinematics_compute_control(
    double time_sec,
    control_input_t *p_control
);

bool kinematics_compute_front_pose(
    const robot_state_t *p_state,
    robot_pose_t *p_pose
);

bool kinematics_step(
    robot_state_t *p_state,
    const control_input_t *p_control,
    double dt_sec,
    robot_pose_t *p_pose
);


#endif /* KINEMATICS_H */
