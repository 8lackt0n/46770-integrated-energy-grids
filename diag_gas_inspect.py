from data_loader import load_data
from network import Network

load, wind_cf, solar_cf = load_data(year=2017)
hours = __import__('pandas').date_range('2017-01-01 00:00','2017-12-31 23:00',freq='h')

net = Network(load, wind_cf, solar_cf, hours=hours)
net.build_network(storage=True, transmission=True, external=True, gas=True)
net.optimize_network()
dispatch, capacities = net.save_results()

# Print capacities for key assets
print('\n=== Capacities summary (relevant assets) ===')
# capacities may be a Series or DataFrame; normalize to Series for easy access
if hasattr(capacities, 'to_dict') and not isinstance(capacities, dict):
    try:
        cap_series = capacities.squeeze()
    except Exception:
        cap_series = capacities
else:
    cap_series = capacities

for name in getattr(cap_series, 'index', []):
    if any(k in name for k in ['OCGT', 'Coal', 'Gas', 'Supply']):
        try:
            print(f"{name}: {cap_series.at[name]}")
        except Exception:
            print(f"{name}: (could not display value)")

print('\n=== Dispatch columns (sample) ===')
print(dispatch.columns.tolist())

# Sum flows for pipelines and electricity lines
pipeline_cols = [c for c in dispatch.columns if 'Gas Pipeline' in c]
electric_cols = [c for c in dispatch.columns if c in ['FIN-SWE','EST-FIN','EST-SWE','EST-LAT']]
print('\nTotal gas pipeline transport (GWh_th):', dispatch[pipeline_cols].abs().sum().sum()/1000 if pipeline_cols else 0)
print('Total electricity transport (GWh_el):', dispatch[electric_cols].abs().sum().sum()/1000 if electric_cols else 0)

# Show installed capacity per country for a few techs
print('\n=== Installed capacities per country (top entries) ===')
for c in ['Estonia','Finland','Sweden','Latvia']:
    for tech in ['Coal','OCGT','Wind','Solar','Battery']:
        matches = [n for n in capacities.index if n.endswith(c) and tech in n]
        if matches:
            for m in matches:
                # capacities may be a DataFrame row; print the row instead of single scalar
                try:
                    row = capacities.loc[m]
                    print(m, row.to_string())
                except Exception:
                    print(m, '(could not display capacity)')

print('\nDone')
# Print marginal costs for key generators/links
print('\n=== Marginal costs (generators/links) ===')
for asset in ['Coal Estonia','OCGT Estonia','OCGT Finland','OCGT Sweden']:
    if asset in net.network.generators.index:
        row = net.network.generators.loc[asset]
        print(asset, 'marginal_cost=', row.get('marginal_cost'), 'capital_cost=', row.get('capital_cost'))
    if asset in net.network.links.index:
        row = net.network.links.loc[asset]
        print(asset, 'marginal_cost=', row.get('marginal_cost'), 'capital_cost=', row.get('capital_cost'))
