// include/KalmanFilter.h

#ifndef KALMAN_FILTER_H
#define KALMAN_FILTER_H

#include <Eigen/Dense>

class KalmanFilter {
public:
    KalmanFilter(double delta = 1e-4, double vt = 1e-3) {
        theta_ = Eigen::Vector2d::Zero();
        P_ = Eigen::Matrix2d::Identity();

        Vw_ = Eigen::Matrix2d::Identity() * delta;
        Vv_ = vt;
    }

    void update(double x, double y) {
        Eigen::RowVector2d H;
        H << 1.0, x;

        P_ = P_ + Vw_;

        double y_pred = H * theta_;
        double e = y - y_pred;

        double Q = H * P_ * H.transpose() + Vv_;

        Eigen::Vector2d K = P_ * H.transpose() / Q;

        theta_ = theta_ + K * e;
        P_ = P_ - K * H * P_;
    }

    double get_intercept() const { return theta_(0); }
    double get_hedge_ratio() const { return theta_(1); }

    double get_spread(double x, double y) const {
        return y - (theta_(0) + theta_(1) * x);
    }

private:
    Eigen::Vector2d theta_;
    Eigen::Matrix2d P_;
    Eigen::Matrix2d Vw_;
    double Vv_;
};

#endif