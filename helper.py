
def annuity(n, r):
    if r > 0:
        return r / (1 - 1/(1+r)**n)
    else:
        return 1/n