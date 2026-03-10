import numpy as np
import scipy.optimize as sco

def apply_shrinkage(cov_mat: np.ndarray, phi: float = 0.7) -> np.ndarray:
    n = cov_mat.shape[0]
    vols = np.sqrt(np.diag(cov_mat))

    avg_corr = (np.sum(cov_mat / np.outer(vols, vols)) - n) / (n * (n - 1))
    const_corr_mat = np.full((n, n), avg_corr)
    np.fill_diagonal(const_corr_mat, 1.0)

    const_cov_mat = np.outer(vols, vols) * const_corr_mat
    cov_mat_hat = (1 - phi) * cov_mat + phi * const_cov_mat
    return cov_mat_hat

def get_msr_weights(er: np.ndarray, cov: np.ndarray) -> np.ndarray:
    noa = len(er)

    def neg_sharpe(weights):
        port_ret = np.dot(weights, er)
        port_vol = np.sqrt(np.dot(weights.T, np.dot(cov, weights)))
        return -port_ret / port_vol

    constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
    bounds = tuple((0.0, 1.0) for _ in range(noa))
    init_guess = noa * [1. / noa,]

    res = sco.minimize(neg_sharpe, init_guess, method='SLSQP', bounds=bounds, constraints=constraints)
    return res.x

def get_rp_weights(cov: np.ndarray) -> np.ndarray:
    noa = len(cov)
    target_risk = np.full(noa, 1.0 / noa)

    def objective(weights):
        port_var = np.dot(weights.T, np.dot(cov, weights))
        marginal_contrib = np.dot(cov, weights)
        risk_contrib = weights * marginal_contrib / port_var
        return np.sum(np.square(risk_contrib - target_risk))

    constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
    bounds = tuple((0.0, 1.0) for _ in range(noa))
    init_guess = noa * [1. / noa,]

    res = sco.minimize(objective, init_guess, method='SLSQP', bounds=bounds, constraints=constraints)
    return res.x