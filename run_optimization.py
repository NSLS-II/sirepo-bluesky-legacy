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


def omea(population, fields):  # needs work to make it generalized
    ind_sol = []
    population.sort()
    print('Getting population individual solutions\nProgress:')
    for i in range(len(population) - 1):
        chk_mean = []
        # indv_pos = {}
        print(str(i + 1), 'of', str(len(population)))
        RE(bp.scan([sirepo_det],
                   fields[0], population[i][0], population[i + 1][0],
                   fields[1], population[i][1], population[i + 1][1],
                   num=3))
        if i == 0:
            ind_sol.append(db[-1].table()['sirepo_det_mean'].values[0])
            ind_sol.append(db[-1].table()['sirepo_det_mean'].values[-1])
            chk_mean.append(db[-1].table()['sirepo_det_mean'].values[1])
            chk_mean.extend(db[-1].table()['sirepo_det_mean'].values[2:-1])
        else:
            ind_sol.append(db[-1].table()['sirepo_det_mean'].values[-1])
            chk_mean.extend(db[-1].table()['sirepo_det_mean'].values[1:-1])
        print()
        # need to get positions of individuals
        # then find max mean between population individuals
        # then replace the next individual with the max in between if it's higher
        # and update population and ind_sol

        #for j in range(len(fields)):
        #    fields[j].set(population[i][j])
        #RE(bps.mov(field0, population[i][0],
        #           field1, population[i][1],
        #           field2, population[i][2],
        #           field3, population[i][3]))
        #sirepo_det.trigger()
        #ind_sol.append(sirepo_det.mean.get())
    #print('********************')

    # loop through each pair of individuals and look for higher evals
    #for h in range(len(population) - 1):
        #if np.all(np.round(population[h], 3) == np.round(population[h + 1], 3)):
        #    pass
        #else:
        #RE(bp.scan([sirepo_det],
        #            fields[0], population[i][0], population[i + 1][0],
        #            fields[1], population[i][1], population[i + 1][1],
        #            num=3))
        #hold_field0_size = db[-1].table()[fields[0].name].values
        #hold_field1_size = db[-1].table()[fields[1].name].values
        #hold_mean = db[-1].table()['sirepo_det_mean'].values
        #chk_field0_size = hold_field0_size[1:-1]
        #chk_field1_size = hold_field1_size[1:-1]
        #chk_mean = hold_mean[1:-1]
        #chk_params = [chk_field0_size, chk_field1_size]

        # find index of max
        #ii = np.argmax(chk_mean)
        # print(chk_field0_size[ii], chk_field1_size[ii], chk_mean[ii])

        #if chk_mean[ii] > ind_sol[i + 1]:
        #    ind_sol[i + 1] = chk_mean[ii]
        #    for k in range(len(population[i])):
        #        # print(chk_params[k][ii])
        #        population[i + 1][k] = chk_params[k][ii]
    print()

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


def best_1(pop, popsize, t_indx, mut, bounds, ind_sol):  # ***
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


def current_to_best_1(pop, popsize, t_indx, mut, bounds, ind_sol):  # ***
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


def diff_ev(bounds, fields, popsize=10, crosspb=0.8, mut=0.05, threshold=1.9, mut_type='rand/1'):  # ***
    # Initial population
    population = []
    init_indv = []
    for i in range(len(fields)):
        init_indv.append(fields[i].get()[0])
    population.append(init_indv)
    #population.append([field0.get()[0], field1.get()[0], field2.get()[0], field3.get()[0]])
    for i in range(popsize - 1):
        indv = []
        for j in range(len(bounds)):
            indv.append(uniform(bounds[j][0], bounds[j][1]))
        population.append(indv)

    init_pop = population[:]
    # plot_pop(fit_func, init_pop, 'Initial population')

    # Evaluate fitness
    # OMEA
    # finds highest evaluation and changes population as new highest eval is discovered
    # may change this later so population isn't changed until all better evals are discovered
    # init_pop.sort()
    new_init_pop, ind_sol = omea(init_pop, fields)  # ***

    pop = new_init_pop[:]

    # plot_pop(fit_func, new_init_pop, 'Better initial population')

    # Termination conditions
    v = 0  # generation number
    consec_best_ctr = 0  # counting successive generations with no change to best value
    old_best_fit_val = 0
    while (not (consec_best_ctr >= 5 and old_best_fit_val >= threshold)):
        if v >= 100:
            print("It's taking too long. Stopping optimization.")
            break
        else:
            print('\nGENERATION ' + str(v + 1))
            print('Working on selection')
            gen_scores = []  # score keeping
            best_gen_sol = []  # holding best scores of each generation
            for w in range(popsize):
                score_trial = []
                score_target = []
                # mutation
                x_t = pop[w]  # target individual
                if mut_type == 'rand/1':
                    v_donor = rand_1(pop, popsize, w, mut, bounds)
                elif mut_type == 'best/1':
                    v_donor = best_1(pop, popsize, w, mut, bounds, ind_sol)  # ***
                elif mut_type == 'current-to-best/1':
                    v_donor = current_to_best_1(pop, popsize, w, mut, bounds, ind_sol)  # ***
                elif mut_type == 'best/2':
                    v_donor = best_2(pop, popsize, w, mut, bounds, ind_sol)  # ***
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
                RE(bps.mov(field0, v_trial[0],
                           field1, v_trial[1]))
                sirepo_det.trigger()
                score_trial = sirepo_det.mean.get()

                #for i in range(len(x_t)):
                #    print('**', str(i + 1), 'of', str(len(x_t)))
                print(str(2 * w + 2), 'of', str(popsize * 2))
                RE(bps.mov(field0, x_t[0],
                           field1, x_t[1]))
                sirepo_det.trigger()
                score_target = sirepo_det.mean.get()

                if score_trial > score_target:
                    pop[w] = v_trial
                    gen_scores.append(score_trial)
                else:
                    gen_scores.append(score_target)

            # score keeping
            # plot_pop(fit_func, pop, 'Gen ' + str(v + 1) + ' population')

            gen_best = max(gen_scores)  # fitness of best individual
            gen_sol = pop[gen_scores.index(max(gen_scores))]  # solution of best individual
            #gen_worst = min(gen_scores)  # fitness of best individual
            worst_indv = pop[gen_scores.index(min(gen_scores))]  # solution of best individual
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
                pop, _ = omea(pop, field0, field1)  # ***

            # introduce a random individual for variation
            for k in range(len(worst_indv)):
                worst_indv[k] = uniform(bounds[k][0], bounds[k][1])

    x_best = best_gen_sol[-1]
    print('\nThe best individual is', x_best, 'with a fitness of', gen_best)
    print('It took', v, 'generations')


sirepo_det = sd.SirepoDetector(sim_id='3eP3NeVp', reg=db.reg)
sirepo_det.select_optic('Aperture1')
param1 = sirepo_det.create_parameter('horizontalSize')
param2 = sirepo_det.create_parameter('verticalSize')
#param3 = sirepo_det.create_parameter('position')
sirepo_det.select_optic('Aperture2')
param4 = sirepo_det.create_parameter('horizontalSize')
param5 = sirepo_det.create_parameter('verticalSize')
#param6 = sirepo_det.create_parameter('position')
#sirepo_det.select_optic('Toroid')
#param7 = sirepo_det.create_parameter('tangentialRadius')
#param8 = sirepo_det.create_parameter('sagittalRadius')
#param9 = sirepo_det.create_parameter('tangentialSize')
#param10 = sirepo_det.create_parameter('sagittalSize')
sirepo_det.read_attrs = ['image', 'mean', 'photon_energy']
sirepo_det.configuration_attrs = ['horizontal_extent',
                                  'vertical_extent',
                                  'shape']
fields = []
fields.append(param1)
fields.append(param2)
fields.append(param4)
fields.append(param5)
# sirepo_det.update_parameters()
#print()
#sirepo_det.trigger()
#print()

diff_ev(bounds=[(3, 5), (.3, .5), (.05, .15), (.05, .15)], fields= fields, popsize=5, crosspb=0.8, mut=0.1, threshold=0, mut_type='best/1')