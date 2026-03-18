
def annuity(n, r):
    if r > 0:
        return r / (1 - 1/(1+r)**n)
    else:
        return 1/n
    
def annualize(value, year_from, year_to, rate=0.07):
    t = year_to - year_from
    return value * (1 + rate) ** t