"""
Module used to validate the results of the simulations using various 
means. These are not quite tests, since we don't have exact values 
to check against, and everything is necessarily approximate.
"""
from __future__ import print_function
from __future__ import division 


import sys
import ercs
import math
import multiprocessing
import numpy as np
import random
import _discsim
from matplotlib import ticker
from matplotlib import pyplot

class ErcsSingleLocusIdentitySimulator(ercs.Simulator):
    """
    Class that calculates identity in state for genes separated by a range
    of distances.
    """
    def setup(self, num_points, max_distance, mutation_rate, accuracy_goal):
        """
        Sets up the simulation so that we calculate identity at the specified
        number of points, the maximum distance between points is
        max_distance and mutation happens at the specified rate. Also
        set the max_time attribute to reflect the specified accuracy_goal.
        """
        self.mutation_rate = mutation_rate
        self.distances = np.linspace(0, max_distance, num_points)
        self.sample = [None, (0, 0)] + [(0, x) for x in self.distances]
        self.max_time = math.log(accuracy_goal) / (-2 * mutation_rate)

    def get_identity(self, seed):
        """
        Returns the probability of identity at all distance classes
        in this replicate.
        """
        pi, tau = self.run(seed)
        mc = ercs.MRCACalculator(pi[0])
        n = len(self.distances)
        F = [0.0 for j in range(n)]
        for j in range(n):
            mrca = mc.get_mrca(1, j + 2)
            if mrca != 0:
                F[j] = math.exp(-2 * self.mutation_rate * tau[0][mrca])
        return F

class SingleLocusIdentitySimulator(object):
    """
    Class that calculates identity in state for genes separated by a range
    of distances.
    """
    def __init__(self, distances, mutation_rate, accuracy_goal, events, **kwargs):
        self.__params = kwargs 
        self.__events = events
        self.__mutation_rate = mutation_rate
        self.__distances = distances
        self.__sample = [(0, 0)] + [(0, x) for x in self.__distances]
        self.__max_time = math.log(accuracy_goal) / (-2 * mutation_rate)

    def run(self, seed):
        """
        Runs the simulation and returns the simulated history.
        """
        self.__params["random_seed"] = seed 
        s = _discsim.Simulator(self.__sample, self.__events, **self.__params)
        s.run(self.__max_time)
        return s.get_history()

    def get_identity(self, seed):
        """
        Returns the probability of identity at all distance classes
        in this replicate.
        """
        pi, tau = self.run(seed)
        mc = ercs.MRCACalculator(pi[0])
        n = len(self.__distances)
        F = [0.0 for j in range(n)]
        for j in range(n):
            mrca = mc.get_mrca(1, j + 2)
            if mrca != 0:
                F[j] = math.exp(-2 * self.__mutation_rate * tau[0][mrca])
        return F

def subprocess_worker(t):
    sim, seed = t
    return sim.get_identity(seed)

def run_replicates(sim, num_replicates, worker_pool):
    args = [(sim, random.randint(1, 2**31)) for j in range(num_replicates)]
    replicates = worker_pool.map(subprocess_worker, args)
    mean_identity = np.mean(np.array(replicates), axis=0)
    return mean_identity


def simple_identity_check(r=1, u=0.125, rate=1, num_parents=1, 
        num_replicates=10000, mutation_rate=1e-6):
    """
    Checks identity using very simple model parameters.
    """
    events = [{"r":r, "u":u, "rate":rate}]
    torus_diameter = 100
    s = _discsim.IdentitySolver(events, 
            torus_diameter=torus_diameter,
            num_quadrature_points=512,
            integration_abserr=1e-6,
            integration_relerr=0,
            integration_workspace_size=1000,
            max_x=50, mutation_rate=mutation_rate,
            num_parents=num_parents)
    s.solve()
    # Set up the simulations
    num_points = 10
    distances = np.linspace(0, 10, num_points)
    sim = SingleLocusIdentitySimulator(distances, mutation_rate, 1e-6,
            events, torus_diameter=torus_diameter,
            num_parents=num_parents)
    workers = multiprocessing.Pool(processes=multiprocessing.cpu_count())
    F_sim= run_replicates(sim, num_replicates, workers)
    F_num = [s.interpolate(x) for x in distances]
    for x, fs, fn in zip(distances, F_sim, F_num):
        print("{0:.1f}\t{1:.6f}\t{2:.6f}".format(x, fs, fn)) 
    pyplot.plot(distances, F_sim, label="Simulation")
    pyplot.plot(distances, F_num, label="Numerical")
    pyplot.legend()
    pyplot.show()

    

def mixed_events_identity_check(num_replicates):
    torus_diameter = 100
    num_points = 50
    max_x = 20
    mutation_rate = 1e-6
    accuracy_goal = 1e-3
    small_events = ercs.DiscEventClass(rate=1.0, r=1, u=0.5)
    large_events = ercs.DiscEventClass(rate=0.1, r=10, u=0.05)
    sim = ErcsSingleLocusIdentitySimulator(torus_diameter)
    sim.setup(num_points, max_x, mutation_rate, accuracy_goal)
    workers = multiprocessing.Pool(4)
    l = [large_events]
    sim.event_classes = l
    #ercs_F = run_replicates(sim, num_replicates, workers)
    #ercs_F.tofile("ercs.dat")
    distances = np.linspace(0, max_x, num_points)
    events = [e.get_low_level_representation() for e in l] 
    sim = SingleLocusIdentitySimulator(distances, mutation_rate, accuracy_goal,
            events, torus_diameter=torus_diameter, num_parents=1,
            pixel_size=20,
            max_occupancy=200)
    discsim_F = run_replicates(sim, num_replicates, workers)
    discsim_F.tofile("discsim-large.dat")
    distances.tofile("x.dat")
    

def plot_mixed_events_identity():
    mutation_rate = 1e-6
    torus_diameter = 100
    x= np.linspace(0, 20, 50)
    events = [{"r":1.0, "u":0.5, "rate":1}]
    s = _discsim.IdentitySolver(events, 
            torus_diameter=torus_diameter,
            num_quadrature_points=512,
            integration_abserr=1e-6,
            integration_relerr=0,
            integration_workspace_size=1000,
            max_x=50, mutation_rate=mutation_rate,
            num_parents=1)
    s.solve()
    F_small = [s.interpolate(y) for y in x]
    events = [{"r":10.0, "u":0.05, "rate":0.1}]
    s = _discsim.IdentitySolver(events, 
            torus_diameter=torus_diameter,
            num_quadrature_points=512,
            integration_abserr=1e-6,
            integration_relerr=0,
            integration_workspace_size=1000,
            max_x=50, mutation_rate=mutation_rate,
            num_parents=1)
    s.solve()
    F_large = [s.interpolate(y) for y in x]
    pyplot.plot(x, F_small)
    pyplot.plot(x, F_large)
    discsim_F = np.fromfile("discsimi_new.dat")
    ercs_F = np.fromfile("ercs.dat")
    x = np.fromfile("x.dat")
    discsim_F_large = np.fromfile("discsim-large.dat")
    pyplot.plot(x, discsim_F, "g--")
    pyplot.plot(x, ercs_F)
    pyplot.plot(x, discsim_F_large)
    pyplot.yscale("log")
    pyplot.ylim(min(discsim_F_large), max(F_small))
    pyplot.gca().yaxis.set_minor_formatter(ticker.ScalarFormatter())
    pyplot.show()


def get_mean_squared_displacement(z, pop):
    """
    Returns the mean squared displacement of the specified population from 
    the specified point.
    """
    d2 = 0.0 
    for p, a in pop:
        d2 += (p[0] - z[0])**2
        d2 += (p[1] - z[1])**2
    n = len(pop)
    return d2 / (n * 2) 


def single_locus_diffusion(u, r, rate):
    """
    Measure the mean squared displacement of lineages for a single 
    locus simulation.
    """
    z = (100, 100)
    sample_size = 10000
    s = 2.25
    L = 100 * s
    sample = [z for j in range(sample_size)]
    events = [{"r":r, "u":u, "rate":rate}]
    s = _discsim.Simulator(sample, events, torus_diameter=L, pixel_size=s,
            max_occupancy=2*sample_size, max_population_size=2*sample_size, 
            num_parents=1)
    T = []
    X = []
    D = []
    S = []
    for j in range(100):
        t = j * 100 * L**2
        s.run(t)
        pop = s.get_population()
        msd = get_mean_squared_displacement(z, pop) 
        t = s.get_time() / L**2
        T.append(t)
        X.append(msd)
        S.append(t * (r**4) * rate * u * math.pi / 2)
        print(T[-1], X[-1], S[-1])
    pyplot.plot(T, X, T, S)
    pyplot.show()

def genetic_wave_1d(u):
    """
    Simulates the wave of genetic ancestors in 1D.
    """
    events = [{"r":1, "u":u, "rate":1}]
    N = int(2 / u)
    L = 100
    sample = [L/2, L/2]
    s = _discsim.Simulator(sample, events, torus_diameter=L, pixel_size=2,
            max_occupancy=2 * N, max_population_size=10000, num_parents=2, 
            dimension=1, num_loci=10000)
    for j in range(5):
        t = j * 1000 * L
        f = s.run(t)
        pop = s.get_population()
        n = [0 for j in range(L)]
        x = [j for j in range(L)]
        print(f, t, s.get_time(), len(pop))
        for y, a in pop:
            j = int(y)
            n[j] += 1
            n[j + 1] += 1
        pyplot.plot(x, n)
        
    pyplot.axhline(0.797 * N)
    pyplot.show()

def pedigree_wave_1d(u):
    """
    Simulates the wave of pedigree ancestors in 1D.
    """
    events = [{"r":1, "u":u, "rate":1}]
    N = int(2 / u)
    L = 100
    sample = [L/2, L/2]
    s = _discsim.Simulator(sample, events, torus_diameter=L, pixel_size=2,
            max_occupancy=2 * N, max_population_size=10000, num_parents=2, 
            dimension=1, num_loci=1, simulate_pedigree=1)
    for j in range(5):
        t = j * 500 * L
        f = s.run(t)
        pop = s.get_population()
        n = [0 for j in range(L)]
        x = [j for j in range(L)]
        print(f, t, s.get_time(), len(pop))
        for y in pop:
            j = int(y)
            n[j] += 1
            n[j + 1] += 1
        pyplot.plot(x, n)
        
    pyplot.axhline(0.797 * N)
    pyplot.show()



def main():
    #simple_identity_check(rate=0.5)
    #simple_identity_check(r=0.73, u=0.133, rate=0.5, num_parents=2, 
    #        num_replicates=10**6, mutation_rate=1e-7)
    #mixed_events_identity_check(10000)
    #plot_mixed_events_identity()
    #single_locus_diffusion(u=0.000125, r=1, rate=1.0)
    #genetic_wave_1d(u=0.005)
    pedigree_wave_1d(u=0.005)

if __name__ == "__main__":
    main()
