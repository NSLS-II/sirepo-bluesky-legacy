from re_config import *
import numpy as np
from random import random, uniform
from multiprocessing import Process
import hashlib

from sirepo_bluesky import SirepoBluesky
import sirepo_detector as sd


# multiprocessing
def run_sim(sim):
    print('Running simulation {}'.format(sim.sim_id))
    sim.run_simulation()


# def main():
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


def omea(positions, fields, grazing_params, grazing_index, autocompute_types):
    evaluations = []
    max_positions = []
    max_evals = []
    print('Getting population individual solutions\nProgress:')
    print(str(1), 'of', str(len(positions)))
    ind_count_params = []
    for t in range(len(fields)):
        ind_count_params.append(fields[t])
        ind_count_params.append(positions[0][t])
    RE(bps.mv(*ind_count_params))
    if len(grazing_params) > 0:
        update_grazing_vectors(grazing_params, grazing_index, fields, autocompute_types)
    RE(bp.count([sirepo_det, *fields]))
    evaluations.append(db[-1].table()['sirepo_det_mean'].values[0])
    for i in range(1, len(positions)):
        chk_mean = []
        print(str(i + 1), 'of', str(len(positions)))
        between_linspace = np.linspace(positions[i - 1], positions[i], 4)
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
            ind_count_params.append(positions[i][t])
        RE(bps.mv(*ind_count_params))
        if len(grazing_params) > 0:
            update_grazing_vectors(grazing_params, grazing_index, fields, autocompute_types)
        RE(bp.count([sirepo_det, *fields]))
        evaluations.append(db[-1].table()['sirepo_det_mean'].values[0])
        # find index of max
        ii = chk_mean.index(np.max(chk_mean))
        max_positions.append(between[ii])
        max_evals.append(chk_mean[ii])

    for i in range(len(max_positions)):
        if max_evals[i] > evaluations[i + 1]:
            evaluations[i + 1] = max_evals[i]
            for k in range(len(positions[i])):
                positions[i + 1][k] = max_positions[i][k]
    return positions, evaluations


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


def update_grazing_vectors(grazing_params, grazing_index, fields, autocompute_types):
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


def mutate(population, strategy, mut, bounds, ind_sol):
    mutated_indv = []
    for i in range(len(population)):
        if strategy == 'rand/1':
            v_donor = rand_1(population, len(population), i, mut, bounds)
        elif strategy == 'best/1':
            v_donor = best_1(population, len(population), i, mut, bounds, ind_sol)
        elif strategy == 'current-to-best/1':
            v_donor = current_to_best_1(population, len(population), i, mut, bounds, ind_sol)
        elif strategy == 'best/2':
            v_donor = best_2(population, len(population), i, mut, bounds, ind_sol)
        elif strategy == 'rand/2':
            v_donor = rand_2(population, len(population), i, mut, bounds)
        mutated_indv.append(v_donor)
    return mutated_indv


def crossover(population, mutated_indv, crosspb):
    crossover_indv = []
    for i in range(len(population)):
        v_trial = []
        x_t = population[i]
        for j in range(len(x_t)):
            crossover_val = random()
            if crossover_val <= crosspb:
                v_trial.append(mutated_indv[i][j])
            else:
                v_trial.append(x_t[j])
        crossover_indv.append(v_trial)
    return crossover_indv


def select(population, crossover_indv, ind_sol, fields, grazing_params, grazing_index, autocompute_types):
    positions = [elm for elm in crossover_indv]
    positions.insert(0, population[0])
    positions, evals = omea(positions, fields, grazing_params, grazing_index, autocompute_types)
    positions = positions[1:]
    evals = evals[1:]
    for i in range(len(evals)):
        if evals[i] < ind_sol[i]:
            population[i] = positions[i]
            ind_sol[i] = evals[i]
    population.reverse()
    ind_sol.reverse()
    return population, ind_sol


def diff_ev(bounds, fields, popsize=5, crosspb=0.8, mut=0.05, threshold=1.9, mut_type='rand/1'):
    # Initial population
    population = []
    init_indv = []
    grazing_params = []
    grazing_index = []
    autocompute_types = []
    best_fitness = [0]
    count_params = []
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

    # Evaluate fitness/OMEA
    init_pop.sort()
    pop, ind_sol = omea(init_pop, fields, grazing_params, grazing_index, autocompute_types)
    pop.reverse()
    ind_sol.reverse()

    # Termination conditions
    v = 0  # generation number
    consec_best_ctr = 0  # counting successive generations with no change to best value
    old_best_fit_val = 0
    while not (consec_best_ctr >= 5 and old_best_fit_val >= threshold):
        print('\nGENERATION ' + str(v + 1))
        print('Working on mutation, crossover, and selection')
        best_gen_sol = []  # hold best scores of each generation
        mutated_trial_pop = mutate(pop, mut_type, mut, bounds, ind_sol)
        cross_trial_pop = crossover(pop, mutated_trial_pop, crosspb)
        pop, ind_sol = select(pop, cross_trial_pop, ind_sol, fields, grazing_params, grazing_index,
                              autocompute_types)

        gen_best = np.max(ind_sol)
        best_indv = pop[ind_sol.index(gen_best)]
        best_gen_sol.append(best_indv)
        best_fitness.append(gen_best)

        print('      > BEST FITNESS:', gen_best)
        print('         > BEST POSITIONS:', best_indv)

        v += 1
        if np.round(gen_best, 3) == np.round(old_best_fit_val, 3):
            consec_best_ctr += 1
            print('Counter:', consec_best_ctr)
        else:
            consec_best_ctr = 0
        old_best_fit_val = gen_best

        if consec_best_ctr >= 5 and old_best_fit_val >= threshold:
            print('Finished')
            break
        else:  # check me later
            # introduce a random individual for variation
            new_pos = ['', '']
            curr_pos = []
            for k in range(len(fields)):
                curr_pos.append(pop[0][k])
            new_pos[0] = curr_pos
            change_index = ind_sol.index(min(ind_sol))
            changed_indv = pop[change_index]
            for k in range(len(changed_indv)):
                changed_indv[k] = uniform(bounds[k][0], bounds[k][1])
            new_pos[1] = changed_indv
            new_pos, randomized_sol = omea(new_pos, fields, grazing_params, grazing_index, autocompute_types)
            new_pos = new_pos[1:]
            randomized_sol = randomized_sol[1:]
            if randomized_sol[0] > ind_sol[change_index]:
                ind_sol[change_index] = randomized_sol[0]
                pop[change_index] = new_pos[0]
            print()
            # count_params.clear()
            # for t in range(len(fields)):
            #     count_params.append(fields[t])
            #     count_params.append(changed_indv[t])
            # RE(bps.mv(*count_params))
            # if len(grazing_params) > 0:
            #     update_grazing_vectors(grazing_params, grazing_index, fields, autocompute_types)
            # RE(bp.count([sirepo_det, *fields]))
            # ind_sol[change_index] = db[-1].table()['sirepo_det_mean'].values[0]

    x_best = best_gen_sol[-1]
    print('\nThe best individual is', x_best, 'with a fitness of', gen_best)
    print('It took', v, 'generations')

    # plot best fitness
    plot_index = np.arange(len(best_fitness))
    plt.figure()
    plt.plot(plot_index, best_fitness)


sim_id = '3eP3NeVp'
sb = SirepoBluesky('http://10.10.10.10:8000')
sb.auth('srw', sim_id)

sirepo_det = sd.SirepoDetector(sim_id=sim_id, reg=db.reg)

field_list = []
sirepo_det.select_optic('Toroid')
field_list.append(sirepo_det.create_parameter('tangentialRadius'))
field_list.append(sirepo_det.create_parameter('grazingAngle'))
sirepo_det.read_attrs = ['image', 'mean', 'photon_energy']
sirepo_det.configuration_attrs = ['horizontal_extent',
                                  'vertical_extent',
                                  'shape']


def main():
    diff_ev(bounds=[(1000, 10000), (5, 10)], fields=field_list, popsize=5,
        crosspb=0.8, mut=0.1, threshold=0, mut_type='rand/1')


if __name__ == '__main__':
    main()
