/*
    FILE: shared_mem.h
    DESC: Interface de comunicacao por memoria compartilhada com heranca de prioridade
    AUTHOR: José Dercy Vieira da Silva Filho
    EMAIL: josedercysilva@gmail.com
    DATE: Out, 2026
    LICENSE: MIT
*/

#ifndef SHARED_MEM_H
#define SHARED_MEM_H

#include <stdbool.h>
#include <stdint.h>
#include "kinematics.h"

bool shared_mem_init(void);
bool shared_mem_destroy(void);

bool shared_mem_write_u(const control_input_t *p_u);
bool shared_mem_read_u(control_input_t *p_u);

bool shared_mem_write_yf(const robot_pose_t *p_yf);
bool shared_mem_read_yf(robot_pose_t *p_yf);

#endif /* SHARED_MEM_H */
