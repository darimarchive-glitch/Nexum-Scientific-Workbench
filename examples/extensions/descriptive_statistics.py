"""Nexum extension example: explicit descriptive statistics, standard library only."""
import statistics

def run(payload):
    values=payload['dataset']['y']
    return {'n':len(values),'mean':statistics.mean(values),'median':statistics.median(values),
            'sample_sd':statistics.stdev(values),'method':'Estatística descritiva da série Y; não realiza inferência causal.'}
