from re_config import *
import numpy as np
from random import random, uniform

import sirepo_detector as sd


def ensure_bounds(vec, bounds):
    # Makes sure each individual stays within bounds and adjusts them if they aren't
    vec_new = []
    # cycle through each variable in vector
    for i in range(len(vec)):
        # variable exceeds the minimum boundary
        if vec[i] < bounds[i][0]:
            vec_new.append(bounds[i][0])
        # variable exceeds the maximum boundary
        if vec[i] > bounds[i][1]:
            vec_new.append(bounds[i][1])
        # the variable is fine
        if bounds[i][0] <= vec[i] <= bounds[i][1]:
            vec_new.append(vec[i])

    return vec_new


def omea(population, fields, grazing_params, grazing_index, autocompute_types):
    ind_sol = []
    population.sort()
    print('Getting population individual solutions\nProgress:')
    print(str(1), 'of', str(len(population)))
    ind_count_params = []
    for t in range(len(fields)):
        ind_count_params.append(fields[t])
        ind_count_params.append(population[0][t])
    RE(bps.mv(*ind_count_params))
    if len(grazing_params) > 0:
        update_grazing_vectors(grazing_params, grazing_index, fields, autocompute_types)
    RE(bp.count([sirepo_det, *fields]))
    ind_sol.append(db[-1].table()['sirepo_det_mean'].values[0])
    for i in range(len(population) - 1):
        chk_mean = []
        print(str(i + 2), 'of', str(len(population)))
        between_linspace = np.linspace(population[i], population[i + 1], 4)
        between = between_linspace[1:-1]
        for j in range(len(between)):
            between_count_params = []
            for t in range(len(fields)):
                between_count_params.append(fields[t])
                between_count_params.append(between[j][t])
            RE(bps.mv(*between_count_params))
            if len(grazing_params) > 0:
                update_grazing_vectors(grazing_params, grazing_index, fields, autocompute_types)
            RE(bp.count([sirepo_det, *fields]))
            chk_mean.append(db[-1].table()['sirepo_det_mean'].values[0])

        ind_count_params.clear()
        for t in range(len(fields)):
            ind_count_params.append(fields[t])
            ind_count_params.append(population[i + 1][t])
        RE(bps.mv(*ind_count_params))
        if len(grazing_params) > 0:
            update_grazing_vectors(grazing_params, grazing_index, fields, autocompute_types)
        RE(bp.count([sirepo_det, *fields]))
        ind_sol.append(db[-1].table()['sirepo_det_mean'].values[0])

        # find index of max
        ii = np.argmax(chk_mean)
        print(between[ii], chk_mean[ii])

        if chk_mean[ii] > ind_sol[i + 1]:
            ind_sol[i + 1] = chk_mean[ii]
            for k in range(len(population[i])):
                population[i + 1][k] = between[ii][k]

    return population, ind_sol


def rand_1(pop, popsize, t_indx, mut, bounds):
    # v = x_r1 + F * (x_r2 - x_r3)
    idxs = [idx for idx in range(popsize) if idx != t_indx]
    a, b, c = np.random.choice(idxs, 3, replace=False)
    x_1 = pop[a]
    x_2 = pop[b]
    x_3 = pop[c]

    x_diff = [x_2_i - x_3_i for x_2_i, x_3_i in zip(x_2, x_3)]
    v_donor = [x_1_i + mut * x_diff_i for x_1_i, x_diff_i in zip(x_1, x_diff)]
    v_donor = ensure_bounds(v_donor, bounds)
    return v_donor


def best_1(pop, popsize, t_indx, mut, bounds, ind_sol):
    # v = x_best + F * (x_r1 - x_r2)
    x_best = pop[ind_sol.index(max(ind_sol))]
    idxs = [idx for idx in range(popsize) if idx != t_indx]
    a, b = np.random.choice(idxs, 2, replace=False)
    x_1 = pop[a]
    x_2 = pop[b]

    x_diff = [x_1_i - x_2_i for x_1_i, x_2_i in zip(x_1, x_2)]
    v_donor = [x_b + mut * x_diff_i for x_b, x_diff_i in zip(x_best, x_diff)]
    v_donor = ensure_bounds(v_donor, bounds)
    return v_donor


def current_to_best_1(pop, popsize, t_indx, mut, bounds, ind_sol):
    # v = x_curr + F * (x_best - x_curr) + F * (x_r1 - r_r2)
    x_best = pop[ind_sol.index(max(ind_sol))]
    idxs = [idx for idx in range(popsize) if idx != t_indx]
    a, b = np.random.choice(idxs, 2, replace=False)
    x_1 = pop[a]
    x_2 = pop[b]
    x_curr = pop[t_indx]

    x_diff1 = [x_b - x_c for x_b, x_c in zip(x_best, x_curr)]
    x_diff2 = [x_1_i - x_2_i for x_1_i, x_2_i in zip(x_1, x_2)]
    v_donor = [x_c + mut * x_diff_1 + mut * x_diff_2 for x_c, x_diff_1, x_diff_2
               in zip(x_curr, x_diff1, x_diff2)]
    v_donor = ensure_bounds(v_donor, bounds)
    return v_donor


def best_2(pop, popsize, t_indx, mut, bounds, ind_sol):  # ***
    # v = x_best + F * (x_r1 - x_r2) + F * (x_r3 - r_r4)
    x_best = pop[ind_sol.index(max(ind_sol))]
    idxs = [idx for idx in range(popsize) if idx != t_indx]
    a, b, c, d = np.random.choice(idxs, 4, replace=False)
    x_1 = pop[a]
    x_2 = pop[b]
    x_3 = pop[c]
    x_4 = pop[d]

    x_diff1 = [x_1_i - x_2_i for x_1_i, x_2_i in zip(x_1, x_2)]
    x_diff2 = [x_3_i - x_4_i for x_3_i, x_4_i in zip(x_3, x_4)]
    v_donor = [x_b + mut * x_diff_1 + mut * x_diff_2 for x_b, x_diff_1, x_diff_2
               in zip(x_best, x_diff1, x_diff2)]
    v_donor = ensure_bounds(v_donor, bounds)
    return v_donor


def rand_2(pop, popsize, t_indx, mut, bounds):
    # v = x_r1 + F * (x_r2 - x_r3) + F * (x_r4 - r_r5)
    idxs = [idx for idx in range(popsize) if idx != t_indx]
    a, b, c, d, e = np.random.choice(idxs, 5, replace=False)
    x_1 = pop[a]
    x_2 = pop[b]
    x_3 = pop[c]
    x_4 = pop[d]
    x_5 = pop[e]

    x_diff1 = [x_2_i - x_3_i for x_2_i, x_3_i in zip(x_2, x_3)]
    x_diff2 = [x_4_i - x_5_i for x_4_i, x_5_i in zip(x_4, x_5)]
    v_donor = [x_1_i + mut * x_diff_1 + mut * x_diff_2 for x_1_i, x_diff_1, x_diff_2
               in zip(x_1, x_diff1, x_diff2)]
    v_donor = ensure_bounds(v_donor, bounds)
    return v_donor


def update_grazing_vectors(grazing_params, grazing_index, fields, autocompute_types):  # ******************
    vectors = []
    for i in range(len(grazing_index)):
        grazing_angle = fields[grazing_index[i]].get()[0]
        nvx = nvy = np.sqrt(1 - np.sin(grazing_angle / 1000) ** 2)
        tvx = tvy = np.sqrt(1 - np.cos(grazing_angle / 1000) ** 2)
        nvz = -tvx
        if autocompute_types[i] == 'horizontal':
            nvy = tvy = 0
        elif autocompute_types[i] == 'vertical':
            nvx = tvx = 0
        for j in range(len(grazing_params)):
            print(5 * i + j)
            if 'normalVectorX' in grazing_params[5 * i + j].name:
                grazing_params[5 * i + j].set(nvx)
            elif 'normalVectorY' in grazing_params[5 * i + j].name:
                grazing_params[5 * i + j].set(nvy)
            elif 'tangentialVectorX' in grazing_params[5 * i + j].name:
                grazing_params[5 * i + j].set(tvx)
            elif 'tangentialVectorY' in grazing_params[5 * i + j].name:
                grazing_params[5 * i + j].set(tvy)
            elif 'normalVectorZ' in grazing_params[5 * i + j].name:
                grazing_params[5 * i + j].set(nvz)
        print()


def diff_ev(bounds, fields, popsize=10, crosspb=0.8, mut=0.05, threshold=1.9, mut_type='rand/1'):
    # Initial population
    population = []
    init_indv = []
    grazing_params = []
    grazing_index = []
    autocompute_types = []
    for i in range(len(fields)):
        init_indv.append(fields[i].get()[0])
        if 'grazingAngle' in fields[i].name and ('Toroid' in fields[i].name or 'Circular Cylinder' in
                                                 fields[i].name or 'Elliptical Cylinder' in fields[i].name):
            grazing_index.append(i)
            if 'Toroid' in fields[i].name:
                optic_name = 'Toroid'
            elif 'Circular' in fields[i].name:
                optic_name = 'Circular Cylinder'
            else:
                optic_name = 'Elliptical Cylinder'
            sirepo_det.select_optic(optic_name)
            autocompute_types.append(sirepo_det.create_parameter('autocomputeVectors'))
            grazing_params.append(sirepo_det.create_parameter('normalVectorX'))
            grazing_params.append(sirepo_det.create_parameter('tangentialVectorX'))
            grazing_params.append(sirepo_det.create_parameter('normalVectorY'))
            grazing_params.append(sirepo_det.create_parameter('tangentialVectorY'))
            grazing_params.append(sirepo_det.create_parameter('normalVectorZ'))
    population.append(init_indv)
    for i in range(popsize - 1):
        indv = []
        for j in range(len(bounds)):
            indv.append(uniform(bounds[j][0], bounds[j][1]))
        population.append(indv)
    init_pop = population[:]

    # need to update grazing angle vectors for accurate mean readings
    # if len(grazing_params) > 0:
    #    update_grazing_vectors(grazing_params, grazing_index, fields, autocompute_types)

    # Evaluate fitness
    # OMEA
    new_init_pop, ind_sol = omea(init_pop, fields, grazing_params, grazing_index, autocompute_types)

    pop = new_init_pop[:]

    # Termination conditions
    v = 0  # generation number
    consec_best_ctr = 0  # counting successive generations with no change to best value
    old_best_fit_val = 0
    while not (consec_best_ctr >= 5 and old_best_fit_val >= threshold):
        if v >= 100:
            print("It's taking too long. Stopping optimization.")
            break
        else:
            print('\nGENERATION ' + str(v + 1))
            print('Working on mutation, crossover, and selection')
            gen_scores = []  # score keeping
            best_gen_sol = []  # holding best scores of each generation
            for w in range(popsize):
                # mutation
                x_t = pop[w]  # target individual
                if mut_type == 'rand/1':
                    v_donor = rand_1(pop, popsize, w, mut, bounds)
                elif mut_type == 'best/1':
                    v_donor = best_1(pop, popsize, w, mut, bounds, ind_sol)
                elif mut_type == 'current-to-best/1':
                    v_donor = current_to_best_1(pop, popsize, w, mut, bounds, ind_sol)
                elif mut_type == 'best/2':
                    v_donor = best_2(pop, popsize, w, mut, bounds, ind_sol)
                elif mut_type == 'rand/2':
                    v_donor = rand_2(pop, popsize, w, mut, bounds)

                # crossover
                v_trial = []
                for u in range(len(x_t)):
                    crossover = random()
                    if crossover <= crosspb:
                        v_trial.append(v_donor[u])
                    else:
                        v_trial.append(x_t[u])

                # selection
                print(str(2 * w + 1), 'of', str(popsize * 2))
                count_params = []
                for t in range(len(fields)):
                    count_params.append(fields[t])
                    count_params.append(v_trial[t])
                RE(bps.mv(*count_params))
                if len(grazing_params) > 0:
                    update_grazing_vectors(grazing_params, grazing_index, fields, autocompute_types)
                RE(bp.count([sirepo_det, *fields]))
                score_trial = db[-1].table()['sirepo_det_mean'].values[0]

                print(str(2 * w + 2), 'of', str(popsize * 2))
                count_params.clear()
                for t in range(len(fields)):
                    count_params.append(fields[t])
                    count_params.append(x_t[t])
                RE(bps.mv(*count_params))
                if len(grazing_params) > 0:
                    update_grazing_vectors(grazing_params, grazing_index, fields, autocompute_types)
                RE(bp.count([sirepo_det, *fields]))
                score_target = db[-1].table()['sirepo_det_mean'].values[0]

                if score_trial > score_target:
                    pop[w] = v_trial
                    gen_scores.append(score_trial)
                else:
                    gen_scores.append(score_target)

            # score keeping
            gen_best = max(gen_scores)  # fitness of best individual
            gen_sol = pop[gen_scores.index(max(gen_scores))]  # solution of best individual
            best_gen_sol.append(gen_sol)

            print('      > GENERATION BEST:', gen_best)
            print('         > BEST SOLUTION:', gen_sol)

            v += 1
            if np.round(gen_best, 3) == np.round(old_best_fit_val, 3):
                consec_best_ctr += 1
                print('Counter:', consec_best_ctr)
            else:
                consec_best_ctr = 0
            old_best_fit_val = gen_best

            # OMEA
            if consec_best_ctr >= 5 and old_best_fit_val >= threshold:
                pass
            else:
                pop, ind_sol = omea(pop, fields, grazing_params, grazing_index, autocompute_types)

            # introduce a random individual for variation
            change_index = ind_sol.index(min(ind_sol))
            changed_indv = pop[change_index]
            for k in range(len(changed_indv)):
                changed_indv[k] = uniform(bounds[k][0], bounds[k][1])
            count_params.clear()
            for t in range(len(fields)):
                count_params.append(fields[t])
                count_params.append(changed_indv[t])
            RE(bps.mv(*count_params))
            if len(grazing_params) > 0:
                update_grazing_vectors(grazing_params, grazing_index, fields, autocompute_types)
            RE(bp.count([sirepo_det, *fields]))
            ind_sol[change_index] = db[-1].table()['sirepo_det_mean'].values[0]

    x_best = best_gen_sol[-1]
    print('\nThe best individual is', x_best, 'with a fitness of', gen_best)
    print('It took', v, 'generations')


sirepo_det = sd.SirepoDetector(sim_id='3eP3NeVp', reg=db.reg)

field_list = []
sirepo_det.select_optic('Toroid')
field_list.append(sirepo_det.create_parameter('tangentialRadius'))
field_list.append(sirepo_det.create_parameter('grazingAngle'))
sirepo_det.select_optic('Circular Cylinder')
field_list.append(sirepo_det.create_parameter('grazingAngle'))
# sirepo_det.select_optic('Elliptical Cylinder')
# field_list.append(sirepo_det.create_parameter('grazingAngle'))
sirepo_det.read_attrs = ['image', 'mean', 'photon_energy']
sirepo_det.configuration_attrs = ['horizontal_extent',
                                  'vertical_extent',
                                  'shape']

diff_ev(bounds=[(1000, 10000), (5, 10), (5, 10)], fields=field_list, popsize=5,
        crosspb=0.8, mut=0.1, threshold=0, mut_type='best/1')