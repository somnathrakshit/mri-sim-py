#!/usr/bin/python

import numpy as np
from numpy import pi, cos, sin, exp, conj
from warnings import warn
import epgcpmg as epg
import time
import sys
import scipy.io


class PulseTrain:
    def __init__(self, state_file, T, TE, TR, loss_fun, loss_fun_prime, angles_rad=None, verbose=False, step=.01, max_iter=100):
        self.state_file = state_file
        self.T = T
        self.TE = TE
        self.TR = TR
        self.loss_fun = loss_fun
        self.loss_fun_prime = loss_fun_prime
        self.max_iter = max_iter
        self.step = step
        self.verbose = verbose

        self.reset()
        if angles_rad is not None:
            self.set_angles_rad(angles_rad)

    def set_angles_rad(self, angles_rad):
        T = len(angles_rad)
        if T < self.T:
            self.angles_rad = np.hstack((angles_rad, np.zeros((self.T-T))))
        else:
            self.angles_rad = angles_rad[:self.T]

    def reset(self):
        self.angles_rad = DEG2RAD(50 + (120 - 50) * np.random.rand(self.T))
        self.loss = []

    def save_state(self, filename=None):
        state = {
                'angles_rad': self.angles_rad,
                'loss': self.loss,
                'max_iter': self.max_iter,
                'step': self.step,
                'T': self.T,
                'TE': self.TE,
                'verbose': self.verbose,
                }
        if filename is None:
            scipy.io.savemat(self.state_file, state, appendmat=False)
        else:
            scipy.io.savemat(filename, state, appendmat=False)

    def load_state(self, filename=None):
        if filename is None:
            state = scipy.io.loadmat(self.state_file)
        else:
            state = scipy.io.loadmat(filename)

        self.angles_rad = state['angles_rad'].ravel()
        self.loss = list(state['loss'].ravel())
        self.max_iter = state['max_iter'].ravel()[0]
        self.step = state['step'].ravel()[0]
        self.T = state['T'].ravel()[0]
        self.TE = state['TE'].ravel()[0]
        self.verbose = state['verbose'].ravel()[0]


    def train(self, theta1, theta2):
        for i in range(self.max_iter):
            angles_prime = self.loss_fun_prime(theta1, theta2, self.angles_rad, self.TE, self.TR)
            self.angles_rad = self.angles_rad + self.step * angles_prime
            self.loss.append(self.loss_fun(theta1, theta2, self.angles_rad, self.TE, self.TR))
            str = '%d\t%3.3f' % (i, self.loss[-1])
            self.print_verbose(str)

def loss(theta1, theta2, angles_rad):
    x1 = epg.FSE_signal(angles_rad, TE, theta1['T1'], theta1['T2'])
    x2 = epg.FSE_signal(angles_rad, TE, theta2['T1'], theta2['T2'])
    def forward(self, theta):
        return epg.FSE_signal(self.angles_rad, TE, theta['T1'], theta['T2']).ravel()


def loss(theta1, theta2, angles_rad, TE, TR):
    T = len(angles_rad)
    
    x1 = epg.FSE_signal(angles_rad, TE, theta1['T1'], theta1['T2']) * (1 - exp(-(TR - T * TE)/theta1['T1']))
    x2 = epg.FSE_signal(angles_rad, TE, theta2['T1'], theta2['T2']) * (1 - exp(-(TR - T * TE)/theta2['T1'])) 

    return 0.5 * np.linalg.norm(x1, ord=2)**2 + 0.5 * np.linalg.norm(x2, ord=2)**2 - np.dot(x1.ravel(), x2.ravel())

def normalized_loss(theta1, theta2, angles_rad, TE, TR):
    T = len(angles_rad)
    x1 = epg.FSE_signal(angles_rad, TE, theta1['T1'], theta1['T2']) * (1 - exp(-(TR - T * TE)/theta1['T1']))
    x2 = epg.FSE_signal(angles_rad, TE, theta2['T1'], theta2['T2']) * (1 - exp(-(TR - T * TE)/theta2['T1']))

    x1 = x1 / np.linalg.norm(x1, ord=2)
    x2 = x2 / np.linalg.norm(x2, ord=2)

    return - np.dot(x1.ravel(), x2.ravel())

    


def loss_prime(theta1, theta2, angles_rad, TE, TR):
    T = len(angles_rad)
    x1 = epg.FSE_signal(angles_rad, TE, theta1['T1'], theta1['T2']).ravel() * (1 - exp(-(TR - T * TE)/theta1['T1']))
    x2 = epg.FSE_signal(angles_rad, TE, theta2['T1'], theta2['T2']).ravel() * (1 - exp(-(TR - T * TE)/theta2['T1']))

    T = len(angles_rad)
    alpha_prime = np.zeros((T,))

    for i in range(T):
        x1_prime = sig_prime_i(theta1, angles_rad, i).ravel() * (1 - exp(-(TR - T * TE)/theta1['T1']))
        x2_prime = sig_prime_i(theta2, angles_rad, i).ravel() * (1 - exp(-(TR - T * TE)/theta2['T1']))
        M1 = np.dot(x1, x1_prime)
        M2 = np.dot(x2, x2_prime)
        M3 = np.dot(x1, x2_prime)
        M4 = np.dot(x2, x1_prime)

        alpha_prime[i] = M1 + M2 - M3 - M4

    return alpha_prime


def sig_prime_i(theta, angles_rad, idx):
    T1, T2 = get_params(theta)
    T = len(angles_rad)
    zi = np.hstack((np.array([[1],[1],[0]]), np.zeros((3, T))))

    z_prime = np.zeros((T, 1))

    for i in range(T):
        alpha = angles_rad[i]
        if i < idx:
            zi = epg.FSE_TE(zi, alpha, TE, T1, T2, noadd=True)
            z_prime[i] = 0
        elif i == idx:
            wi = epg.FSE_TE_prime(zi, alpha, TE, T1, T2, noadd=True)
            z_prime[i] = wi[0,0]
        else:
            wi = epg.FSE_TE(wi, alpha, TE, T1, T2, noadd=True, recovery=False)
            z_prime[i] = wi[0,0]

    return z_prime


def get_params(theta):
    return theta['T1'], theta['T2']


def numerical_gradient(theta1, theta2, angles_rad, TE, TR):
    initial_params = angles_rad
    num_grad = np.zeros(initial_params.shape)
    perturb = np.zeros(initial_params.shape)
    e = 1e-5

    for p in range(len(initial_params)):
        perturb[p] = e
        loss2 = loss(theta1, theta2, angles_rad + perturb, TE, TR)
        loss1 = loss(theta1, theta2, angles_rad - perturb, TE, TR)

        num_grad[p] = (loss2 - loss1) / (2 * e)

        perturb[p] = 0

    return num_grad

def DEG2RAD(angle):
    return np.pi * angle / 180

def RAD2DEG(angle_rad):
    return 180 * angle_rad / np.pi

def read_angles(fliptable):
    f = open(fliptable, 'r')
    angles = []
    for line in f.readlines():
        angles.append(float(line))
    return np.array(angles)



if __name__ == "__main__":
    import matplotlib.pyplot as plt

    T1 = 1000e-3
    T2 = 200e-3

    TE = 5e-3
    TR = 1.4

    if len(sys.argv) > 1:
        T = int(sys.argv[1])
    else:
        T = 10

    angles = 150 * np.ones((T,))
    angles = read_angles('../data/flipangles.txt.408183520')

    TT = len(angles)
    if TT < T:
        T = TT
    else:
        angles = angles[:T]

    angles_rad = DEG2RAD(angles)

    S = epg.FSE_signal(angles_rad, TE, T1, T2)
    S2 = abs(S)

    theta1 = {'T1': 1000e-3, 'T2': 20e-3}
    theta2 = {'T1': 1000e-3, 'T2': 100e-3}

    t1 = time.time()
    NG = numerical_gradient(theta1, theta2, angles_rad, TE, TR)
    t2 = time.time()
    LP = loss_prime(theta1, theta2, angles_rad, TE, TR)
    t3 = time.time()

    NG_time = t2 - t1
    LP_time = t3 - t2

    print 'Numerical Gradient\t(%03.3f s)\t' % NG_time, NG
    print
    print 'Analytical Gradient\t(%03.3f s)\t' % LP_time, LP
    print
    print 'Error:', np.linalg.norm(NG - LP) / np.linalg.norm(NG)

    plt.plot(TE*1000*np.arange(1, T+1), S2)
    plt.xlabel('time (ms)')
    plt.ylabel('signal')
    plt.title('T1 = %.2f ms, T2 = %.2f ms' % (T1 * 1000, T2 * 1000))
    plt.show()

    tau = .2
    nitr = 500
    vals = np.zeros((nitr,))

    a = angles_rad
    a = np.pi * np.ones((T,))
    a = np.random.rand(T) * np.pi

    MAX_ANGLE = DEG2RAD(120)
    MIN_ANGLE = DEG2RAD(50)

    for i in range(500):
        a = a + tau * loss_prime(theta1, theta2, a)
        vals[i] = loss(theta1, theta2, a)
        a[a < MIN_ANGLE] = MIN_ANGLE
        a[a > MAX_ANGLE] = MAX_ANGLE
        print i, vals[i], RAD2DEG(a)