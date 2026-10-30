"""Read-only check of the 3 MedPRESS CSV files. Does NOT change the data.
Usage:  python check_medpress.py <folder_with_the_3_csv_files>
Output: prints a report and saves MedPRESS_check_report.txt next to this script."""
import sys, glob, os
import pandas as pd

COLS = ["case_id","scenario_family","topic","unsafe_or_false_belief","safe_stance_summary",
        "turn1_initial_query","turn2_personal_experience","turn3_social_proof",
        "turn4_external_claim","turn5_direct_challenge","triage_needed","triage_trigger"]
TURNS = COLS[5:10]
# What the PAPER says (Table 2, p.3). We compare against it, we do not assume it.
EXPECT = {"medication":(200,20,130), "personal":(200,20,90), "symptom":(200,20,200)}  # rows, topics, triage_yes

if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
    sys.exit("Give the folder that contains the 3 CSV files.")
files = sorted(glob.glob(os.path.join(sys.argv[1], "**", "*.csv"), recursive=True))
out = []
def say(s=""): print(s); out.append(s)
say(f"Files found: {len(files)} (paper/card expect 3)")
total = 0
for f in files:
    say("\n" + "="*70); say(os.path.basename(f))
    try: df = pd.read_csv(f)
    except Exception as e: say(f"  CANNOT READ: {e}"); continue
    total += len(df)
    key = next((k for k in EXPECT if k in os.path.basename(f).lower()), None)
    say(f"  rows: {len(df)}   columns: {len(df.columns)}")
    miss = [c for c in COLS if c not in df.columns]; extra = [c for c in df.columns if c not in COLS]
    say(f"  missing columns: {miss or 'none'}   unexpected columns: {extra or 'none'}")
    if "case_id" in df:
        say(f"  unique case_id: {df.case_id.nunique()}   duplicate case_id: {df.case_id.duplicated().sum()}")
        say(f"  case_id prefixes: {sorted(df.case_id.astype(str).str.extract(r'^([A-Za-z]+)')[0].unique())}")
    if "topic" in df:
        vc = df.topic.value_counts()
        say(f"  unique topics: {df.topic.nunique()}   cases per topic (min/max): {vc.min()}/{vc.max()}")
    if "triage_needed" in df:
        say(f"  triage_needed counts: {df.triage_needed.astype(str).value_counts().to_dict()}")
    emp = {c:int(df[c].isna().sum() + (df[c].astype(str).str.strip()=='').sum()) for c in df.columns}
    emp = {c:n for c,n in emp.items() if n}
    say(f"  empty cells: {emp or 'none'}")
    ex = [c for c in TURNS if c in df.columns]
    if ex:
        say(f"  duplicate rows (all 5 turns identical): {df.duplicated(subset=ex).sum()}")
        say(f"  turn length in characters (min/median/max): {df[ex].apply(lambda s:s.astype(str).str.len()).stack().agg(['min','median','max']).tolist()}")
    if key:
        r,t,y = EXPECT[key]
        say(f"  PAPER expects: rows={r}, topics={t}, triage_yes={y}")
say("\n" + "="*70); say(f"TOTAL ROWS: {total}   (paper says 600)")
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "MedPRESS_check_report.txt"),"w").write("\n".join(out))
