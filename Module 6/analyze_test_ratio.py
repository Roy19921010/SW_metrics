from pathlib import Path
import csv

def estimate_test_coverage(repo_path: Path):
    java_files = list(repo_path.rglob("*.java"))
    if not java_files: return 0.0
    test_files = [f for f in java_files if 'test' in str(f).lower() or 'test' in f.name.lower() or f.name.endswith('Test.java')]
    return len(test_files)/len(java_files)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-r","--repo",default="/home/eiinluj/phd/rdi-datastream-dump-archiver")
    parser.add_argument("-o","--output",default="test_coverage.csv")
    args = parser.parse_args()

    repo_path=Path(args.repo).resolve()
    coverage=estimate_test_coverage(repo_path)
    print(f"Test coverage estimate: {coverage:.3f}")

    with open(args.output,'w',newline='',encoding='utf-8') as f:
        import csv
        writer=csv.DictWriter(f,fieldnames=['test_coverage_est'])
        writer.writeheader()
        writer.writerow({'test_coverage_est':round(coverage,4)})
    print(f"Test coverage saved to {args.output}")

if __name__=="__main__":
    main()
