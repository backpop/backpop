from scipy.stats import norm, multivariate_normal
from nautilus import Prior, Sampler
import numpy as np

def likelihood(param_dict):
    x = np.array([param_dict['a'], param_dict['b'], param_dict['c']])
    return multivariate_normal.logpdf(
        x, mean=np.zeros(3), cov=[[1, 0, 0.90], [0, 1, 0], [0.90, 0, 1]])

def main():
    prior = Prior()
    prior.add_parameter('a', dist=(-5, +5))
    prior.add_parameter('b', dist=(-5, +5))
    prior.add_parameter('c', dist=norm(loc=0, scale=2.0))

    sampler = Sampler(prior, likelihood, n_live=1000, pool=2)
    sampler.run(verbose=True)

if __name__ == "__main__":
    main() 