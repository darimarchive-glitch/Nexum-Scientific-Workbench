"""Divided differences for experimental or simulated titration curves."""
import math


def analyze_curve(points):
    pts = [(float(x), float(y)) for x, y in points]
    if not 5 <= len(pts) <= 10000:
        raise ValueError('Informe entre 5 e 10000 pares volume,pH.')
    if any(not math.isfinite(x) or not math.isfinite(y) or x < 0 for x, y in pts):
        raise ValueError('Volumes devem ser não negativos e todos os valores finitos.')
    if any(b[0] <= a[0] for a, b in zip(pts, pts[1:])):
        raise ValueError('Informe volumes estritamente crescentes, sem repetições.')
    first = [((a[0]+b[0])/2, (b[1]-a[1])/(b[0]-a[0])) for a,b in zip(pts,pts[1:])]
    second = [((a[0]+b[0])/2, (b[1]-a[1])/(b[0]-a[0])) for a,b in zip(first,first[1:])]
    peak = max(range(len(first)), key=lambda i: abs(first[i][1]))
    candidates=[]
    for i in range(1,len(second)-1):
        if second[i][1] == 0 and second[i-1][1]*second[i+1][1] < 0:
            candidates.append(second[i][0])
    for (x0,y0),(x1,y1) in zip(second,second[1:]):
        if y0*y1<0:
            candidates.append(x0-y0*(x1-x0)/(y1-y0))
    # Boundary peaks and flat/linear curves do not establish an equivalence.
    estimate=None
    if 0<peak<len(first)-1 and candidates and abs(first[peak][1])>1e-12:
        nearby=min(candidates,key=lambda x:abs(x-first[peak][0]))
        if first[peak-1][0] <= nearby <= first[peak+1][0]:estimate=nearby
    return {'first_derivative':first,'second_derivative':second,
            'peak_volume_ml':first[peak][0], 'estimated_equivalence_ml':estimate}
