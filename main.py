from ingest import Ingestor
from metrics import MetricsCalculator

if __name__ == "__main__":
    filepath = r"C:\Users\ninja\Documents\code\diabetes-analysis\data\test.csv"
    ingestor = Ingestor(filepath = filepath)
    calculator = MetricsCalculator(cgm_df=ingestor.cgm_data)
    calculator.print_clinical_report()