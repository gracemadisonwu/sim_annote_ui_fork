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


def auto_run_speaker_multi_channel(file_path: str, whisper_results_file: str, denoise: bool = False, denoise_prop: float = 0.1,
                 verification_threshold: float = 0.2):
    file_processor = MultiChannelFileProcessor(file_path, whisper_results_file, denoise, denoise_prop, verification_threshold)
    file_processor.process()
    return file_processor.speaker_results

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--whisper_initial_labels", type=str, default="data/whisper_results.json")
    parser.add_argument("--ground_truth_labels", type=str, default="data/ground_truth_labels.json")
    parser.add_argument("--audio_path", type=str, default="data/audios/audio1.wav")
    parser.add_argument("--output_path", type=str, default="data/all_results.json")
    args = parser.parse_args()
    whisper_initial_labels = args.whisper_initial_labels
    ground_truth_labels = args.ground_truth_labels
    ground_truth_labels = json.load(open(ground_truth_labels))

    speaker_results = auto_run_speaker_multi_channel(args.audio_path, args.whisper_initial_labels, denoise=True, denoise_prop=0.2, verification_threshold=0)
    speaker_results = speaker_results["segments"]
    evaluator = Evaluator(ground_truth_labels, speaker_results, None)
    results = evaluator.evaluate()
    json.dump(results, open(args.output_path, "w"))