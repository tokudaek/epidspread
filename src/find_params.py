#!/usr/bin/env python3
"""Find best params
"""

import argparse
import logging
from os.path import join as pjoin
from logging import debug, info

from multiprocessing import Pool
import numpy as np
import scipy
import scipy.optimize
import igraph
import networkx as nx
import time
import pandas as pd
from optimized import generate_waxman_adj


def run_one_experiment(r):
    """short-description

    Args:
    param1, param2

    Returns:
    ret
    """
    time.sleep(np.random.rand()*2)
    nvertices = 625
    # nvertices = 22500
    avgdegree = 6
    maxnedges = nvertices * nvertices //2
    domain = [0, 0, 1, 1]
    n = nvertices

    def rgr(r):
        # '625,6': 0.056865545,
        # '10000,6': 0.0139,
        # '22500,6': 0.00925,
        g = igraph.Graph.GRG(nvertices, r)
        err =  np.mean(g.degree()) - avgdegree
        with open('/home/keiji/temp/grg_params.csv', 'a') as fh:
            fh.write('{},{}\n'.format(r, err))
        # print(r, err)

    alpha = 0.015
    def waxman(b):
        adjlist, x, y = generate_waxman_adj(nvertices, maxnedges, alpha, b,
                                            domain[0], domain[1], domain[2], domain[3])
        adjlist = adjlist.astype(int).tolist()

        g = igraph.Graph(n, adjlist)
        err =  np.mean(g.degree()) - avgdegree

        # with open('/tmp/waxman_params.csv', 'a') as fh:
            # fh.write('{},{},{}\n'.format(r, np.mean(g.degree()), err))
        return err

    err = waxman(r)
    print('r:{}, err:{}'.format(r, err))
    # rgr(r)


def generate_waxman(n, maxnedges, alpha, beta, domain=(0, 0, 1, 1)):
    adjlist, x, y = generate_waxman_adj(n, maxnedges, alpha, beta,
                                        domain[0], domain[1], domain[2], domain[3])
    adjlist = adjlist.astype(int).tolist()

    g = igraph.Graph(n, adjlist)
    g.vs['x'] = x
    g.vs['y'] = y
    return g

def get_waxman_params(nvertices, avgdegree, alpha):
    maxnedges = nvertices * nvertices // 2

    radiuscatalog = {
    }

    k = '{},{}'.format(nvertices, avgdegree)
    if k in radiuscatalog.keys():
        return radiuscatalog[k], alpha

    def f(b):
        g = generate_waxman(nvertices, maxnedges, alpha=alpha, beta=b)
        return np.mean(g.degree()) - avgdegree

    b1 = 0.0001
    b2 = 1000
    beta = scipy.optimize.brentq(f, b1, b2, xtol=0.001, rtol=0.05)
    return beta, alpha

def main():
    
    parser = argparse.ArgumentParser(description=__doc__)
    #parser.add_argument('--outdir', required=True, help='Output directory')
    args = parser.parse_args()

    logging.basicConfig(format='[%(asctime)s] %(message)s',
    datefmt='%Y%m%d %H:%M', level=logging.DEBUG)


    nvertices = 22500
    for alpha in [0.0025,0.005,0.0075,0.01,0.0125,0.015,0.0175,0.02,0.0225,0.2]:
        beta = []
        for i in range(5):
            try:
                beta_, alpha_ = get_waxman_params(nvertices, 6, alpha)
                beta.append(beta_)
            except:
                pass
        print(alpha, len(beta), np.mean(beta), np.std(beta))
    return

    n = 10
    # params = [0.00189]*n
    # params = [0.1, 0.15, 0.2, 0.25, 0.3]
    params = [4.4, 4.5, 4.6, 4.7]
    # params = list(np.arange(0.00183, 0.00191, 0.00001))
    # print(params)
    n = len(params)
    pool = Pool(n)
    pool.map(run_one_experiment, params)
    return
    # df = pd.read_csv('/home/keiji/temp/grg_params.csv', header=None,
    df = pd.read_csv('/tmp/waxman_params.csv', header=None,
                names=['v'])
    print(params[0], np.mean(df.v))
    # print('checkpoint')

if __name__ == "__main__":
    main()
