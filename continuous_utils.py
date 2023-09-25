from mdp import LavaWorld
import numpy as np
import random
from scipy.optimize import minimize
from scipy.optimize import LinearConstraint
import math

rseed = 168
random.seed(rseed)
np.random.seed(rseed)

# Lavaworld variables
N = 6
traj_length = 20
num_start_pos = 10
num_rand_policies = 10
starting_positions = np.random.uniform(0, 1, (num_start_pos, 2))
rand_policies = []  # set of random policies for each starting position
rewards = np.array([round(t, 1) for t in np.linspace(0, 1, N)])

def generate_random_policies(env = "lavaworld"):
    if env == "lavaworld":
        ### Random geneneration types (RGT) ###
        # A: completely random; generate a bunch of points, ensuring ending at (1, 1), and sort by x-value. 0.048489625937646816
        # B: same as above, but don't even sort the points. 0.024790507333516485
        # C: generate random waypoints starting from left side and ending at (1, 1), but ensuring equal spacing. 9.810941615629709
        # D: RRT. 
        rgt = "A"
        for start_pos in starting_positions:
            rand_policies_start_pos = []
            if rgt == "A":
                for _ in range(num_rand_policies):  # generate num_rand_policies random trajectories for this starting position
                    rand_policy = np.random.uniform(0, 1, (traj_length - 1, 2))
                    rand_policy = np.append(rand_policy, [1.0, 1.0]).reshape(traj_length, 2)
                    rand_policy = rand_policy[np.argsort((lambda x: x[:, 0])(rand_policy))]
                    rand_policies_start_pos.append(rand_policy)
            elif rgt == "B":
                for _ in range(num_rand_policies):  # generate num_rand_policies random trajectories for this starting position
                    rand_policy = np.random.uniform(0, 1, (traj_length - 1, 2))
                    rand_policy = np.append(rand_policy, [1.0, 1.0]).reshape(traj_length, 2)
                    rand_policies_start_pos.append(rand_policy)
            elif rgt == "C":
                for _ in range(num_rand_policies):  # generate num_rand_policies random trajectories for this starting position
                    xs = np.linspace(start_pos[0], 1.0, traj_length)
                    ys = np.linspace(start_pos[1], 1.0, traj_length)
                    rand_policy = np.array(list(zip(xs, ys)))
                    rand_policies_start_pos.append(rand_policy)
            elif rgt == "D":
                def distance(point1, point2):
                    return math.sqrt((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2)
                def generate_random_waypoint(curr_pos, end_pos, num_waypoints, current_index):
                    d = distance(curr_pos, end_pos) / (num_waypoints - current_index - 1)
                    angle_range_rad = math.radians(90)
                    min_x, max_x = 0, 1  # define the boundaries of the unit square
                    min_y, max_y = 0, 1
                    angle = np.random.uniform(0, angle_range_rad)
                    x = curr_pos[0] + d * math.cos(angle)
                    y = curr_pos[1] + d * math.sin(angle)
                    x = min(max(x, min_x), max_x)  # ensure the generated point is within the unit square
                    y = min(max(y, min_y), max_y)
                    return (x, y)
                def rrt_path(start_pos, end_pos, num_waypoints):
                    path = [start_pos]
                    current_index = 0
                    for _ in range(num_waypoints - 2):
                        new_waypoint = generate_random_waypoint(path[current_index], end_pos, num_waypoints, current_index)
                        path.append(new_waypoint)
                        current_index += 1
                    path.append(end_pos)
                    return path
                for _ in range(num_rand_policies):  # generate num_rand_policies random trajectories for this starting position
                    rand_policy = np.array(rrt_path(start_pos, (1.0, 1.0), traj_length))
                    rand_policies_start_pos.append(rand_policy)
            rand_policies.append(rand_policies_start_pos)

def random_lavaworld(tt = None):
    lava = np.asarray([np.random.random()*0.5 + 0.25, np.random.random()*0.5 + 0.25])
    if tt is None:
        theta = np.random.choice(rewards)
        # theta_idx = np.random.choice(np.array(range(8)))
        # theta = np.array([[0, 0.5], [0, 1], [0.5, 0], [0.5, 0.5], [0.5, 1], [1, 0], [1, 0.5], [1, 1]])[theta_idx]
    else:
        theta = tt
    lavaworld = LavaWorld(theta, lava)
    return lavaworld

def trajreward(xi, theta, lava, traj_length):
    ## Reward ##
    # xi = xi.reshape(n,2)
    # smoothcost = 0
    # for idx in range(n-1):
    #     smoothcost += np.linalg.norm(xi[idx+1,:] - xi[idx,:])**2
    # avoidreward = 0
    # for idx in range(n):
    #     avoidreward += np.linalg.norm(xi[idx,:] - lava) / n
    # return -(np.exp(-smoothcost**2) + (1 - np.exp(-(theta * avoidreward)**2)))

    ## Cost ##
    xi = xi.reshape(traj_length, 2)
    smoothcost = 0
    for idx in range(1, traj_length - 1):
        smoothcost += np.linalg.norm(xi[idx+1, :] - xi[idx, :])**2 # higher means not as smooth
    avoidcost = 0
    for idx in range(1, traj_length):
        # avoidcost -= np.linalg.norm(xi[idx, :] - lava) / n # more negative means farther from lava
        avoidcost += 1 / np.linalg.norm(xi[idx, :] - lava) # higher if closer to lava
    avoidcost /= traj_length
    
    # Exponential transformation
    # smoothcost = 1 - np.exp(-smoothcost**2)
    # avoidcost = np.exp(-avoidcost**2)

    # 1D vs 2D theta
    # return theta[0] * smoothcost + theta[1] * avoidcost
    # return (1 - theta) * smoothcost + theta * avoidcost
    return smoothcost + theta * avoidcost

def get_optimal_policy(theta, lava_position, generating_demo = False, start_pos = None):
    # hyperparameters
    if start_pos is None:
        dist_from_lava = np.linalg.norm(np.array([0, 0]) - np.array([lava_position]))
        start_x = np.random.uniform(0, 1)
        start_y = np.random.uniform(0, 1)
    else:
        start_x = start_pos[0]
        start_y = start_pos[1]
    xi0 = np.zeros((traj_length, 2))
    xi0[:, 0] = np.linspace(start_x, 1, traj_length)
    xi0[:, 1] = np.linspace(start_y, 1, traj_length)
    if generating_demo:
        print("This demo is starting from", start_x, start_y)
    xi0 = xi0.reshape(-1)
    B = np.zeros((4, traj_length * 2))
    B[0, 0] = 1
    B[1, 1] = 1
    B[2, -2] = 1
    B[3, -1] = 1
    cons = LinearConstraint(B, [start_x, start_y, 1, 1], [start_x, start_y, 1, 1])
    res = minimize(trajreward, xi0, args=(theta, lava_position, traj_length), method='SLSQP', constraints=cons)
    return res.x.reshape(traj_length, 2)

def get_human(theta, lava, type, generating_demo = False, start_pos = None):
    vision_radius = 0.3
    xi_star = get_optimal_policy(theta, lava, generating_demo = generating_demo, start_pos = start_pos)
    if type == "optimal":
        return xi_star
    n = xi_star.shape[0]
    if type == "regular":
        stoptime_lb = n - 1
        noise_variance = 0.00001
    elif type == "noise":
        stoptime_lb = n - 1
        noise_variance = 100
    elif type == "counterfactual":
        stoptime_lb = 0
        noise_variance = 0.05
    detect, eta = False, 0.0
    xi = np.zeros((n,2))
    xi0 = np.zeros((n,2))
    xi0[:,0] = np.linspace(0, 1, n)
    xi0[:,1] = np.linspace(0, 1, n)
    state = xi[0,:]
    for idx in range(1,n):
        dist2lava = np.linalg.norm(state - lava)
        if dist2lava < vision_radius:
            detect = True
        if detect:
            eta += 0.1
            if eta > 1.0:
                eta = 1.0
        action = eta * (xi_star[idx,:] - state) + (1 - eta) * (xi0[idx,:] - state)
        state += action + np.random.normal(0, noise_variance, 2)
        xi[idx,:] = state
    stoptime = np.random.randint(stoptime_lb, n)
    xi[stoptime:,0] = np.linspace(xi[stoptime,0], 1, n - stoptime)
    xi[stoptime:,1] = np.linspace(xi[stoptime,1], 1, n - stoptime)
    xi[0,:] = [0,0]
    xi[-1,:] = [1,1]
    return xi

def generate_optimal_demo(env, generating_demo = False):
    theta_star = env.feature_weights # true reward function
    lava = env.lava
    demo = get_human(theta_star, lava, type = "optimal", generating_demo = generating_demo)
    return demo

def generate_random_demo(env, n):
    lava = env.lava
    demo = np.array([])
    demo = np.append(demo, [0, 0])
    for _ in range(n - 2):
        demo = np.append(demo, [random.random(), random.random()])
    demo = np.append(demo, [[1, 1]])
    for i in range(len(demo)):
        if all(demo[i] == lava):
            demo[i][0] -= 0.0001
            demo[i][1] += 0.0001
            break
    demo = demo.reshape(n, 2)
    return demo

def value_iteration(env, epsilon = 0.0001):
    pass

def policy_evaluation(policy, env):
    return      

def policy_evaluation_stochastic(env):
    return

def get_nonpessimal_policy(env, epsilon = 0.0001, V = None):
    return get_human(env.feature_weights, env.lava, type = "noise")

def logsumexp(x):
    max_x = np.max(x)
    sum_exp = 0.0
    for xi in x:
        sum_exp += np.exp(xi - max_x)
    return max(x) + np.log(sum_exp)

def calculate_q_values(env, storage = None, V = None, epsilon = 0.0001):
    return

def arg_max_set(values, eps = 0.0001):
    return

def calculate_policy_accuracy(env, map_pi, opt_pi = None):
    n = len(map_pi)
    acc = 0
    print("Map policy starts from", (map_pi[0][0], map_pi[0][1]))
    if opt_pi is None:
        opt_pi = get_optimal_policy(env.feature_weights, env.lava, start_pos = (map_pi[0][0], map_pi[0][1]))
        print("Optimal policy starts from", (opt_pi[0][0], opt_pi[0][1]))
    for i in range(n):
        acc += np.linalg.norm(np.array(map_pi)[i, :] - np.array(opt_pi)[i, :]) <= 0.1
        # acc += map_pi[i][0] == opt_pi[i][0] or map_pi[i][1] == opt_pi[i][1]
    return acc / n

def get_trajectory_and_reward(env, start_pos):
    trajectory = get_optimal_policy(env.feature_weights, env.lava, start_pos)
    reward = trajreward(trajectory, env.feature_weights, env.lava, traj_length)
    return reward

def calculate_expected_value_difference(test_env, eval_env, rn = False):
    # A = E_(starting positions)[reward(optimal trajectory for R', R')]
    # B = E_(starting positions)[reward(optimal trajectory for R_MAP, R')]
    # C = E_(all random trajectories)[reward(random trajectory, R')]
    # nEVD(R', R_MAP) = (A - B) / (A - C), where R' <=> test_env and R_MAP <=> eval_env
    V_opt = 0
    V_eval = 0
    V_rand = 0
    for i in range(num_start_pos):
        start_pos = starting_positions[i]
        opt_traj = get_optimal_policy(test_env.feature_weights, test_env.lava, start_pos = start_pos)
        eval_traj = get_optimal_policy(eval_env.feature_weights, eval_env.lava, start_pos = start_pos)
        V_opt += trajreward(opt_traj, test_env.feature_weights, test_env.lava, traj_length) / num_start_pos
        V_eval += trajreward(eval_traj, test_env.feature_weights, test_env.lava, traj_length) / num_start_pos
        if rn:
            V_rand_start_pos = 0
            for j in range(num_rand_policies):
                V_rand_start_pos += trajreward(rand_policies[i][j], test_env.feature_weights, test_env.lava, traj_length) / num_rand_policies
            V_rand += V_rand_start_pos / num_start_pos
    if rn:
        evd = (V_opt - V_eval) / (V_opt - V_rand)
        return evd
    else:
        return V_opt - V_eval

def comparison_grid(env, possible_rewards, possible_policies):
    # possible_policies = [get_optimal_policy(pr, env.lava) for pr in possible_rewards]
    values = [[0 for j in range(len(possible_rewards))] for i in range(len(possible_policies))]
    for i in range(len(possible_policies)):
        for j in range(len(possible_rewards)):
            value = trajreward(possible_policies[i], possible_rewards[j], env.lava, traj_length)
            # print("For theta_{} = {} and policy {}, cost is {}".format(j, possible_rewards[j], i, value))
            values[i][j] = value
    return np.array(values)

def calculate_percent_improvement(env, base_policy, eval_policy, epsilon = 0.000001, actual = False):
    # V_base = trajreward(base_policy, env.feature_weights, env.lava, traj_length)
    V_base = 1e-3
    V_eval = trajreward(eval_policy, env.feature_weights, env.lava, traj_length)
    improvement = (V_eval - V_base) / (np.abs(V_base) + epsilon)
    return (improvement + 1)/2

def sample_l2_ball(k):
    sample = np.random.randn(k)
    return sample / np.linalg.norm(sample)

def listify(arr):
    new_arr = []
    arr = list(arr)
    for elem in arr:
        try:
            new_arr.append(list(elem))
        except TypeError:
            new_arr.append(elem)
    return new_arr