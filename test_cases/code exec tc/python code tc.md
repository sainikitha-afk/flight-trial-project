#### Notes:



data is a list of dicts (one dict per selected FlightID).



Allowed builtins: print, len, sum, max, min, range, sorted, int, float, str, isinstance.



Use f-strings for formatting (e.g. f"{avg:.3f}") — that works fine.



Select 1+ Flight IDs in the multi-select before running.



* #### CE-01: Quick peek at the data



&nbsp;		



* #### CE-02: Compute average Speed safely



speeds = \[]

for rec in data:

    try:

        speeds.append(float(rec.get("Speed", 0)))

    except:

        pass



avg = (sum(speeds) / len(speeds)) if speeds else 0.0

print(f"count={len(speeds)}  sum={sum(speeds)}  avg={avg:.3f}")



* #### CE-03: Nicely formatted table for common columns

cols = \["FlightID","Speed","Altitude","BrakeTemp","Current\_A","Voltage\_V","FuelFlow","Pressure\_Pa","Temp\_C"]



\# print header

print(",".join(cols))



\# print rows

for rec in data:

    values = \[str(rec.get(c, "")) for c in cols]

    print(",".join(values))



* #### CE-04: Filter flights by threshold



\# list flights where Current\_A > 220

high = \[]

for rec in data:

    try:

        if float(rec.get("Current\_A", 0)) > 20:

            high.append(rec.get("FlightID"))

    except:

        pass



print("High current flights:", ", ".join(high) if high else "(none)")

