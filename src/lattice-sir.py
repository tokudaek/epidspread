#!/usr/bin/env python
""" Simulation of two dynamics: mobility and infection over a lattice
"""

import argparse
import logging
import os, sys
from os.path import join as pjoin
from logging import debug, info
from itertools import product

import string
import igraph
import networkx as nx
import numpy as np
import pandas as pd
import copy
from matplotlib import cm
from matplotlib import pyplot as plt
from mpl_toolkits import mplot3d
import math
from subprocess import Popen, PIPE
from datetime import datetime
from multiprocessing import Pool
import pickle as pkl


########################################################## Defines
SUSCEPTIBLE = 0
INFECTED = 1
RECOVERED = 2
EPSILON = 1E-5
MAX = sys.maxsize

#############################################################
def run_one_experiment_given_list(l):
    run_lattice_sir(*l)

##########################################################
def run_lattice_sir(mapside, nei, istoroid , nepochs , s0 , i0 , r0 ,
                    beta, gamma , graddist , gradmean , gradstd ,
                    autoloop_prob , plotzoom , plotlayout , plotrate , outdir ,
                    nprocs , randomseed, expidx):
    """Main function

    Args:
    params

    Returns:
    ret
    """


    cfgdict = {}
    keys = ['mapside', 'nei', 'istoroid' , 'nepochs' , 's0' , 'i0' , 'r0' ,
            'beta', 'gamma' , 'graddist' , 'gradmean' , 'gradstd' ,
            'autoloop_prob' , 'plotzoom' , 'plotlayout' , 'plotrate' , 'outdir' ,
            'nprocs' , 'randomseed']
    args = [mapside, nei, istoroid , nepochs , s0 , i0 , r0 ,
            beta, gamma , graddist , gradmean , gradstd ,
            autoloop_prob , plotzoom , plotlayout , plotrate , outdir ,
            nprocs , randomseed]
    for i, k in enumerate(keys):
        cfgdict[k] = args[i]

    cfg = pd.DataFrame.from_dict(cfgdict, 'index', columns=['data'])

    ########################################################## Cretate outdir
    # expidxstr = '{:03d}'.format(expidx)
    outdir = pjoin(outdir, expidx)

    if not os.path.exists(outdir):
        os.mkdir(outdir)
    ##########################################################
    info('exp:{} Copying config file ...'.format(expidx))
    cfg['data'].to_json(pjoin(outdir, 'config.json'), force_ascii=False)

    dim = [mapside, mapside]
    N = s0 + i0 + r0
    nvertices = mapside**2 # square lattice
    status = np.ndarray(N, dtype=int)
    status[0: s0] = SUSCEPTIBLE
    status[s0:s0+i0] = INFECTED
    status[s0+i0:] = RECOVERED
    np.random.shuffle(status)
    info('exp:{} Generated random distribution of S, I, R ...'.format(expidx))

    visual = {}
    visual["bbox"] = (mapside*10*plotzoom, mapside*10*plotzoom)
    visual["margin"] = mapside*plotzoom
    visual["vertex_size"] = 10*plotzoom

    totalnsusceptibles = [s0]
    totalninfected = [i0]
    totalnrecovered = [r0]

    aux = '' if istoroid else 'non-'
    info('exp:{} Generating {}toroidal lattice with dim ({}, {}) ...'.format(expidx,
                                                                             aux,
                                                                             mapside,
                                                                             mapside,
                                                                             ))
    g = igraph.Graph.Lattice(dim, nei, directed=False, mutual=True, circular=istoroid)

    # visualize_static_graph_layouts(g, 'config/layouts_lattice.txt', outdir);
    layout = g.layout(plotlayout)

    ntransmissions = np.zeros(nvertices, dtype=int)
    ########################################################## Distrib. of particles
    info('exp:{} Generating uniform distribution of agents in the lattice ...'.format(expidx))
    nparticles = np.ndarray(nvertices, dtype=int)
    aux = np.random.rand(nvertices) # Uniform distrib
    nparticles = np.round(aux / (np.sum(aux)) *N).astype(int)

    diff = N - np.sum(nparticles) # Correct rounding differences on the final number
    for i in range(np.abs(diff)):
        idx = np.random.randint(nvertices)
        nparticles[idx] += np.sign(diff) # Initialize number of particles per vertex

    particles = [None]*nvertices # Initialize indices of particles per vertex
    aux = 0
    for i in range(nvertices):
        particles[i] = list(range(aux, aux+nparticles[i]))
        aux += nparticles[i]
    nparticlesstds = [np.std([len(x) for x in particles])]

    ########################################################## Distrib. of gradients
    info('exp:{} Initializing gradients distribution ...'.format(expidx))
    g = initialize_gradients(g, graddist, gradmean, gradstd)
    info('exp:{} Exporting relief map...'.format(expidx))
    aux = pd.DataFrame(g.vs['gradient'])
    aux.to_csv(pjoin(outdir, 'attraction.csv'), index=False, header=['gradient'])

    ########################################################## Plot gradients
    if plotrate > 0:
        info('exp:{} Generating plots for epoch 0'.format(expidx))

        aux = np.sum(g.vs['gradient'])
        gradientscolors = [ [c, c, c] for c in g.vs['gradient']]
        # gradientscolors = [1, 1, 1]*g.vs['gradient']
        gradsum = float(np.sum(g.vs['gradient']))
        gradientslabels = [ '{:2.3f}'.format(x/gradsum) for x in g.vs['gradient']]
        outgradientspath = pjoin(outdir, 'gradients.png')
        igraph.plot(g, target=outgradientspath, layout=layout,
                    vertex_shape='rectangle', vertex_color=gradientscolors,
                    vertex_frame_width=0.0, **visual)      

        b = 0.1 # For colors definition
        ########################################################## Plot epoch 0
        nsusceptibles, ninfected, nrecovered, \
            _, _, _  = compute_statuses_sums(status, particles, nvertices, [], [], [])
        plot_epoch_graphs(-1, g, layout, visual, status, nvertices, particles,
                          N, b, outgradientspath, nsusceptibles, ninfected, nrecovered,
                          totalnsusceptibles, totalninfected, totalnrecovered, outdir)

    for ep in range(nepochs):
        if ep % 10 == 0:
            info('exp:{}, t:{}'.format(expidx, ep))
        particles = step_mobility(g, particles, autoloop_prob)
        aux = np.std([len(x) for x in particles])
        nparticlesstds.append(aux)
        status, ntransmissions = step_transmission(g, status, beta, gamma, particles,
                                                      ntransmissions)
      
        nsusceptibles, ninfected, nrecovered, \
            totalnsusceptibles, totalninfected, \
            totalnrecovered  = compute_statuses_sums(status, particles, nvertices,
                                                     totalnsusceptibles, totalninfected,
                                                     totalnrecovered)
        if plotrate > 0 and ep % plotrate == 0:
            plot_epoch_graphs(ep, g, layout, visual, status, nvertices, particles,
                              N, b, outgradientspath, nsusceptibles, ninfected, nrecovered,
                              totalnsusceptibles, totalninfected, totalnrecovered, outdir)

    ########################################################## Enhance plots
    if plotrate > 0:
        # cmd = "mogrify -gravity south -pointsize 24 " "-annotate +50+0 'GRADIENT' " \
            # "-annotate +350+0 'S' -annotate +650+0 'I' -annotate +950+0 'R' " \
            # "{}/concat*.png".format(outdir)
        # proc = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        # stdout, stderr = proc.communicate()

        animationpath = pjoin(outdir, 'animation.gif')
        cmd = 'convert -delay 120 -loop 0  {}/concat*.png "{}"'.format(outdir, animationpath)
        proc = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        stdout, stderr = proc.communicate()
        print(stderr)

    ########################################################## Export to csv
    info('exp:{} Exporting transmissions locations...'.format(expidx))
    print(aux)
    aux = pd.DataFrame(ntransmissions)
    aux.to_csv(pjoin(outdir, 'ntranmissions.csv'), index=False, header=['ntransmission'])
    ########################################################## Export to csv
    info('exp:{} Exporting S, I, R data'.format(expidx))
    aux = np.array([totalnsusceptibles, totalninfected, totalnrecovered, nparticlesstds]).T
    pd.DataFrame(aux).to_csv(pjoin(outdir, 'sir.csv'), header=['S', 'I', 'R', 'nparticlesstd'],
                             index=True, index_label='t')

    ########################################################## Plot SIR over time
    info('exp:{} Generating plots for counts of S, I, R'.format(expidx))
    fig, ax = plt.subplots(1, 1)
    plot_sir(totalnsusceptibles, totalninfected, totalnrecovered, fig, ax, outdir)
    info('exp:{} Finished. Results are in {}'.format(expidx, outdir))

def visualize_static_graph_layouts(g, layoutspath, outdir):
    layouts = [line.rstrip('\n') for line in open(layoutspath)]
    for l in layouts:
        info(l)
        try:
            igraph.plot(g, target=pjoin(outdir, l + '.png'), layout=g.layout(l),
                        vertex_color='lightgrey',
                        vertex_label=list(range(g.vcount())))
        except Exception:
            pass

########################################################## Distrib. of gradients
def initialize_gradients_peak(g):
    """Initizalition of gradients with a peak at 0

    Args:
    g(igraph.Graph): graph instance

    Returns:
    igraph.Graph: graph instance with attribute 'gradient' updated
    """
    g.vs[0]['gradient'] = 100
    return g

##########################################################
def multivariate_normal(x, d, mean, cov):
    """pdf of the multivariate normal when the covariance matrix is positive definite.
    Source: wikipedia"""
    return (1. / (np.sqrt((2 * np.pi)**d * np.linalg.det(cov))) *
            np.exp(-(np.linalg.solve(cov, x - mean).T.dot(x - mean)) / 2))

##########################################################
def gaussian(xx, mu, sig):
    """pdf of the normal distrib"""
    x = np.array(xx)
    return np.exp(-np.power(x - mu, 2.) / (2 * np.power(sig, 2.)))

##########################################################
def set_gaussian_weights_recursive(g, curid, nextvs, dist, mu, sigma):
    supernewgrad = gaussian(dist+1, mu, sigma)
    visitted.add(curid)
    for v in g.neighbors(curid):
        g.vs[v]['gradient'] = supernewgrad 

    visitted.remove(curid)

##########################################################
def initialize_gradients_gaussian(g, mu=0, sigma=1):
    """Initizalition of gradients with a single gaussian

    Args:
    g(igraph.Graph): graph instance
k
    Returns:
    igraph.Graph: graph instance with attribute 'gradient' updated
    """

    # centeridx = int((g.vcount())/2)
    if g.vcount() % 2 == 0:
        centeridx = int((g.vcount())/2 - np.sqrt(g.vcount())/2) 
    else:
        centeridx = int((g.vcount())/2)
    dists = g.shortest_paths(centeridx)
    gauss = gaussian(dists, mu, sigma).flatten()
    for v in range(len(gauss)):
        g.vs[v]['gradient'] = gauss[v]

    return g

##########################################################
def initialize_gradients(g, method='peak', mu=0, sigma=1):
    """Initialize gradients with some distribution

    Args:
    g(igraph.Graph): graph instance

    Returns:
    igraph.Graph: graph instance with attribute 'gradient' updated
    """

    g.vs['gradient'] = 10

    if method == 'uniform':
        return g
    if method == 'peak':
        return initialize_gradients_peak(g)
    elif method == 'gaussian':
        return initialize_gradients_gaussian(g, mu, sigma)

def step_mobility(g, particles, autoloop_prob):
    """Give a step in the mobility dynamic

    Args:
    g(igraph.Graph): instance of a graph
    particles(list of list): the set of particle ids for each vertex
    autoloop_prob(float): probability of staying in the same place

    Returns:
    list of list: indices of the particles in each vertex
    """
    particles_fixed = copy.deepcopy(particles) # copy to avoid being altered

    for i, _ in enumerate(g.vs): # For each vertex
        numvparticles = len(particles_fixed[i])
        neighids = g.neighbors(i)
        n = len(neighids)
        gradients = g.vs[neighids]['gradient']

        if np.sum(gradients) == 0:
            gradients = np.ones(n) / n
        else:
            gradients /= np.sum(gradients)

        for j, partic in enumerate(particles_fixed[i]): # For each particle in this vertex
            if np.random.rand() <= autoloop_prob: continue
            if neighids == []: continue
            neighid = np.random.choice(neighids, p=gradients)
            particles[i].remove(partic)
            particles[neighid].append(partic)
    return particles

##########################################################
def step_transmission(g, status, beta, gamma, particles, ntransmissions):
    """Give a step in the transmission dynamic

    Args:
    g(igraph.Graph): instance of a graph
    status(list): statuses of each particle
    beta(float): contagion chance
    gamma(float): recovery chance
    particles(list of list): the set of particle ids for each vertex

    Returns:
    list: updated statuses
    """

    statuses_fixed = copy.deepcopy(status)
    for i, _ in enumerate(g.vs):
        statuses = statuses_fixed[particles[i]]
        N = len(statuses)
        nsusceptible = len(statuses[statuses==SUSCEPTIBLE])
        ninfected = len(statuses[statuses==INFECTED])
        nrecovered = len(statuses[statuses==RECOVERED])

        indsusceptible = np.where(statuses_fixed==SUSCEPTIBLE)[0]
        indinfected = np.where(statuses_fixed==INFECTED)[0]
        indrecovered = np.where(statuses_fixed==RECOVERED)[0]

        x  = np.random.rand(nsusceptible*ninfected)
        y  = np.random.rand(ninfected)
        numnewinfected = np.sum(x <= beta)
        numnewrecovered = np.sum(y <= gamma)
        if numnewinfected > nsusceptible: numnewinfected = nsusceptible
        if numnewrecovered > ninfected: numnewrecovered = ninfected

        print(numnewinfected)
        ntransmissions[i] += numnewinfected
        status[indsusceptible[0:numnewinfected]] = INFECTED
        status[indinfected[0:numnewrecovered]] = RECOVERED
    return status, ntransmissions

##########################################################
def compute_statuses_sums(status, particles, nvertices, totalnsusceptibles,
                          totalninfected, totalnrecovered):
    """Compute the sum of each status

    Args:
    params

    Returns:
    nsusceptibles(list of int): number of susceptibles per vertex
    ninfected(list of int): number of infected per vertex
    nrecovered(list of int): number of recovered per vertex
    """

    nsusceptibles = np.array([ np.sum(status[particles[i]]==SUSCEPTIBLE) for i in range(nvertices)] )
    ninfected = np.array([ np.sum(status[particles[i]]==INFECTED) for i in range(nvertices)] )
    nrecovered = np.array([ np.sum(status[particles[i]]==RECOVERED) for i in range(nvertices)] )
    totalnsusceptibles.append(np.sum(nsusceptibles))
    totalninfected.append(np.sum(ninfected))
    totalnrecovered.append(np.sum(nrecovered))
    return nsusceptibles, ninfected, nrecovered, totalnsusceptibles, totalninfected, totalnrecovered
##########################################################
def plot_epoch_graphs(ep, g, layout, visual, status, nvertices, particles,
                      N, b, outgradientspath, nsusceptibles, ninfected, nrecovered,
                      totalnsusceptibles, totalninfected, totalnrecovered, outdir):
    susceptiblecolor = []
    infectedcolor = []
    recoveredcolor = []

    for z in nsusceptibles:
        zz = [0, math.log(z, N), 0] if z*N > 1 else [0, 0, 0] # Bug on log(1,1)
        susceptiblecolor.append(zz)
    for z in ninfected:
        zz = [math.log(z, N), 0, 0] if z*N > 1 else [0, 0, 0]
        infectedcolor.append(zz)
    for z in nrecovered:
        zz = [0, 0,  math.log(z, N)] if z*N > 1 else [0, 0, 0]
        recoveredcolor.append(zz)  
        
    outsusceptiblepath = pjoin(outdir, 'susceptible{:02d}.png'.format(ep+1))
    outinfectedpath = pjoin(outdir, 'infected{:02d}.png'.format(ep+1))
    outrecoveredpath = pjoin(outdir, 'recovered{:02d}.png'.format(ep+1))

    igraph.plot(g, target=outsusceptiblepath, layout=layout, vertex_shape='rectangle', vertex_color=susceptiblecolor, vertex_frame_width=0.0, **visual)      
    igraph.plot(g, target=outinfectedpath, layout=layout, vertex_shape='rectangle', vertex_color=infectedcolor, vertex_frame_width=0.0, **visual)      
    igraph.plot(g, target=outrecoveredpath, layout=layout, vertex_shape='rectangle', vertex_color=recoveredcolor, vertex_frame_width=0.0, **visual)      

    outconcatpath = pjoin(outdir, 'concat{:02d}.png'.format(ep+1))
    proc = Popen('convert {} {} {} {} +append {}'.format(outgradientspath,
                                                         outsusceptiblepath,
                                                         outinfectedpath,
                                                         outrecoveredpath,
                                                         outconcatpath),
                 shell=True, stdout=PIPE, stderr=PIPE)
    stdout, stderr = proc.communicate()

##########################################################
def plot_sir(s, i, r, fig, ax, outdir):
    ax.plot(s, 'g', label='Susceptibles')
    ax.plot(i, 'r', label='Infected')
    ax.plot(r, 'b', label='Recovered')
    ax.legend()
    fig.savefig(pjoin(outdir, 'sir.png'))

def random_string(length=8):
    """Generate a random string of fixed length """
    letters = np.array(list(string.ascii_lowercase + ' '))
    aux = ''.join(np.random.choice(letters, size=length))
    return aux.replace(' ', 'z')
##########################################################
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', nargs='?', default='config/toy01.json')
    args = parser.parse_args()

    logging.basicConfig(format='[%(asctime)s] %(message)s',
    datefmt='%Y%m%d %H:%M', level=logging.INFO)

    cfg = pd.read_json(args.config, typ='series') # Load config

    outdir = pjoin(cfg.outdir[0], datetime.now().strftime('%Y%m%d_%H%M') + '-latticesir')
    if os.path.exists(outdir):
        ans = input(outdir + ' exists. Do you want to continue? ')
        if ans.lower() not in ['y', 'yes']:
            info('Aborting')
            return
    else:
        os.mkdir(outdir)

    cfg.outdir = [outdir]

    aux = list(product(*cfg))
    params = []
    fh = open(pjoin(outdir, 'exps.csv'), 'w')
    colnames = ['idx'] + (list(cfg.index))
    fh.write(','.join(colnames) + '\n')

    for i in range(len(aux)):
        hash = random_string(3)
        params.append(list(aux[i]) + [hash])
        pstr = [str(x) for x in [hash] + list(aux[i])]
        fh.write(','.join(pstr) + '\n')
    fh.close()

    if cfg.nprocs[0] <= 1:
        [ run_one_experiment_given_list(p) for p in params ]
    else:
        pool = Pool(cfg.nprocs[0])
        pool.map(run_one_experiment_given_list, params)


if __name__ == "__main__":
    main()
