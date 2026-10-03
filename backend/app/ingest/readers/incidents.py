"""Read `Incident Database.xlsx`, sheet `Incident Database` (header on row 3)."""

import pandas as pd

COLUMN_MAP = {
    "Serial No": "serial_no",
    "MTO No.": "mto_no",
    "AR No.": "ar_no",
    "Plant": "plant_code",
    "Tag Number": "tag_number",
    "Eq. Class": "eq_class",
    "Date of Occur.": "date_of_occur",
    "Risk Case Title": "risk_case_title_raw",
    "Highest Impact": "highest_impact",
    "Pre-Risk": "pre_risk",
    "Risk Score": "risk_score",
    "PIC (RCA)": "pic_rca",
    "Overall Status": "overall_status",
    "Discipline": "discipline",
    "Eq. Type": "eq_type",
    "Component": "component",
    "F Mechanism": "f_mechanism",
    "Downtime (hrs)": "downtime_hrs",
    "Act. Loss (k US$)": "act_loss_kusd",
    "Pot. Loss (k US$)": "pot_loss_kusd",
    "Total Loss (k US$)": "total_loss_kusd",
    "RCA Due Date": "rca_due_date",
    "Month - Year": "month_year",
}


def read_incidents(path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="Incident Database", header=2)
    df = df.rename(columns=COLUMN_MAP)
    df = df[list(COLUMN_MAP.values())]
    for date_col in ("date_of_occur", "rca_due_date"):
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce").dt.strftime("%Y-%m-%d")
    df["ar_no"] = df["ar_no"].where(df["ar_no"].astype(str).str.lower() != "n/a", None)
    df["rca_due_date"] = df["rca_due_date"].where(pd.notna(df["rca_due_date"]), None)
    return df
