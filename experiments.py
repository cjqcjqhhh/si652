import numpy as np
import pandas as pd
import random
import matplotlib.pyplot as plt
random.seed(42)

#--- constants ---#

N = 1000 # number of repeated experiments 
n = 10 # number of agents
m = 12 # number of topics
p = 15 # number of slots

#--- statistic functions ---#

def generatePreference(n, m, p):
    """
    Generate preference ordering for the setting.
    """
    pref = {}
    for i in range(n):
        tp = list(range(m)) # topic preference ordering
        random.shuffle(tp)
        sp = list(range(p)) # time slot preference ordering
        random.shuffle(sp)
        pref[i] = (tp, sp)

    return pref

def countUtility(i, t, s, pref):
    """
    Count overall utility for agent i for topic t at time s.
    """
    tp, sp = pref[i]
    ut = m - tp.index(t)
    us = p - sp.index(s)
    return ut * us

def countFairness(utilities):
    return np.var(utilities)

def countSocialWelfare(utilities):
    return np.sum(utilities)

#--- Assignment Algorithm ---#

def rand():
    """
    Random assign topic and time slot for each agent.
    """
    result = {}
    topics = random.sample(range(m), n) # topic assignment
    slots = random.sample(range(p), n) # time slot assignment 
    for i, (t, s) in enumerate(zip(topics, slots)):
        result[i] = (t, s)
    return result

def topfirst(pref):
    """
    Assign top preferred topic and time slot for each agent.
    If multiple agents have the same top preference, randomly pick a winner (here we simply pick the first one).
    """
    result = {}
    topics = []
    slots = []
    for i in range(n):
        tp, sp = pref[i]
        for j in range(m):
            if tp[j] not in topics:
                topics.append(tp[i])
                break
        for j in range(p):
            if sp[j] not in slots:
                slots.append(sp[i])
                break
    for i, (t, s) in enumerate(zip(topics, slots)):
        result[i] = (t, s)
    return result

def voting(pref):
    """
    Each agent votes for their preferred topics and time slots.
    Agents with top votes on a topic or time slot win. If draw, randomly pick a winner.
    There are two strategies for an agents:
    1. Assign all their votes to the top preferred topic and time slots.
    2. Spread the votes according to their preference ordering.
    """
    votes = {}
    sum1 = sum(range(m))
    sum2 = sum(range(p))
    for i in range(n):
        tp, sp = pref[i]
        if random.randint(0, 1):
            votes[i] = (
                [1 if j == tp[0] else 0 for j in range(m)],
                [1 if j == sp[0] else 0 for j in range(p)]
            )
        else:
            votes[i] = (
                [tp[j] / sum1 for j in range(m)],
                [sp[j] / sum2 for j in range(p)]
            )
    
    result = {}
    topics = [-1 for i in range(n)]
    slots = [-1 for i in range(n)]

    # filter most popular topics and time slots
    vt_list = [] # vote for topics
    vs_list = [] # vote for time slots
    for i, (vt, vs) in votes.items():
        vt_list.append(np.array(vt))
        vs_list.append(np.array(vs))
    vt_sum = sum(vt_list)
    popular_topics = np.argpartition(vt_sum, -n)[-n:]
    vs_sum = sum(vs_list)
    popular_slots = np.argpartition(vs_sum, -n)[-n:]

    # assign topic and time slots according to vote
    for t in popular_topics:
        vote = [vt_list[i][t] for i in range(n)]
        rank = sorted(zip(vote, range(n)), reverse=True)
        for v, i in rank:
            if topics[i] == -1:
                topics[i] = t
                break
    for s in popular_slots:
        vote = [vs_list[i][s] for i in range(n)]
        rank = sorted(zip(vote, range(n)), reverse=True)
        for v, i in rank:
            if slots[i] == -1:
                slots[i] = s
                break
        
    for i, (t, s) in enumerate(zip(topics, slots)):
        result[i] = (t, s)
    return result
    
def socialwelfare():
    """
    Assign topics and time slot to maximize social welfare.
    It is an NP-hard problem. Emitted here.
    """
    pass

if __name__ == "__main__":
    # Start Experiments
    statistics = {
        "Random": np.zeros(2),
        "Top-first": np.zeros(2),
        "Voting": np.zeros(2)
    }
    for i in range(N):
        pref = generatePreference(n, m, p)

        # Random Assignment
        res = rand()
        utilities = [countUtility(k, v[0], v[1], pref) for k, v in res.items()]
        statistics["Random"] += np.array([countFairness(utilities), countSocialWelfare(utilities)])

        # Top-first Assignment
        res = topfirst(pref)
        utilities = [countUtility(k, v[0], v[1], pref) for k, v in res.items()]
        statistics["Top-first"] += np.array([countFairness(utilities), countSocialWelfare(utilities)])
        
        # Voting Assignment
        res = voting(pref)
        utilities = [countUtility(k, v[0], v[1], pref) for k, v in res.items()]
        statistics["Voting"] += np.array([countFairness(utilities), countSocialWelfare(utilities)])

    for k, v in statistics.items():
        statistics[k] = statistics[k] / N

    # Plot the statistics
    statistics = pd.DataFrame(statistics, index=["Fairness Score", "Social Welfare Score"]).T
    print(statistics)
    # plt.style.use('ggplot')
    statistics.plot.bar(figsize=(6,3), rot=0)
    plt.show()