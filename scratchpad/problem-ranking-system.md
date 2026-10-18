# Problem Ranking System

[LeetCodeBot](https://github.com/xDDoubleTea/LeetCodeBot)

## Score of a Problem

For problem $i$, the score is defined by

$$
S_i = \sum_{j=1}^{C}c_jw_j
$$

where

- $c_j$ is an evaluation of the criterion $j$,
- $w_j$ is the weight of the criterion $j$,
- $C$ is the total number of criteria.

Note on the range of $c_j$ and $w_j$:

$$
\begin{cases}0\le c_j\le 1\\w_j\in\mathbb{N}\cup\{0\}\end{cases}
$$

for each $1\le j\le C$.

## Criteria

### Difficulty

- As a tie breaker, prefer medium -> easy -> hard.

### Skill stats

- Tags that show up frequently gets higher score

### Recent AC

- Check Recent AC problems tags
- Maybe too hard come back to this later.

### Attempting

Every attempting problems should appear in front of the list, i.e., steps should be:

1. Rank all attempting, put them on the list.
2. Rank all non-attempting, append to the list.

### Problem AC rate

- higher -> evaluation higher

### Description length

- longer -> evalutaion lower

### Tie breaker

- randomly shuffle

## Filters

- Database
- Premium
- AC'ed
