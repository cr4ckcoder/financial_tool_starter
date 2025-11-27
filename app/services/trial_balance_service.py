from typing import List
# stub for Trial Balance service
def process_upload(file_path: str, work_id: int):
    # Real implementation: call csv parser, bulk insert TrialBalanceEntry records
    return {"status": "ok", "work_id": work_id, "file": file_path}
