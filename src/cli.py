import argparse, json
from .pipeline import analyze

def main():
    ap=argparse.ArgumentParser(description="Bowling scoreboard extraction")
    ap.add_argument("--video",default="bowling_scoreboard.mp4")
    args=ap.parse_args()
    result=analyze(args.video)
    print(json.dumps(result["data"],indent=2))

if __name__=="__main__": main()
