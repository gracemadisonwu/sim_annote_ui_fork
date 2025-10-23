from speaker_identification import FileProcessor
import json
from pyannote.core import Segment, Timeline, Annotation
from pyannote.metrics.diarization import DiarizationErrorRate
from jiwer import wer
import os
import tqdm
from sklearn.metrics import precision_recall_fscore_support, accuracy_score
from argparse import ArgumentParser
from auto_run_speaker import Evaluator
from auto_run_speaker import auto_run_speaker
import copy
from multi_channel_speaker_identification import MultiChannelFileProcessor


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--ground_truth_labels", type=str, default="data/ground_truth_labels.json")
    parser.add_argument("--predictions", type=str, default="data/predictions.json")
    parser.add_argument("--output_path", type=str, default="data/all_results.json")
    args = parser.parse_args()
    ground_truth_labels = args.ground_truth_labels
    ground_truth_labels = json.load(open(ground_truth_labels))

    speaker_results = json.load(open(args.predictions))
    evaluator = Evaluator(ground_truth_labels, speaker_results, None)
    results = evaluator.evaluate()
    json.dump(results, open(args.output_path, "w"))