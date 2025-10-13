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

def rewrite_speakers(ground_truth_labels: dict, speaker_duration: int):
    new_labels = copy.deepcopy(ground_truth_labels)
    for seg in new_labels:
        seg["speaker"] = ""
    speaker_durations = {}
    for i, s in enumerate(ground_truth_labels):
        if s["speaker"] not in speaker_durations:
            speaker_durations.update({s["speaker"]: []})
        speaker_durations[s["speaker"]].append((i, s["end"] - s["start"]))
    
    for speaker in speaker_durations:
        num_segments = len([x for x in speaker_durations[speaker] if x[1] < speaker_duration])
        if num_segments > 0:
            speaker_durations[speaker] = [x for x in speaker_durations[speaker] if x[1] < speaker_duration]
        else:
            speaker_durations[speaker] = [x for x in speaker_durations[speaker] if x[1] < speaker_duration + 1]
        speaker_durations[speaker] = sorted(speaker_durations[speaker], key=lambda x: x[1], reverse=True)
    for speaker in speaker_durations:
        total_duration = 0
        for i, duration in speaker_durations[speaker]:
            if total_duration > speaker_duration:
                break
            total_duration += duration
            new_labels[i]["speaker"] = speaker
    return new_labels

    

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--whisper_initial_labels", type=str, default="data/whisper_results.json")
    parser.add_argument("--ground_truth_labels", type=str, default="data/ground_truth_labels.json")
    parser.add_argument("--video_path", type=str, default="data/videos/video1.mp4")
    parser.add_argument("--output_path", type=str, default="data/all_results.json")
    args = parser.parse_args()
    whisper_initial_labels = args.whisper_initial_labels
    ground_truth_labels = args.ground_truth_labels
    ground_truth_labels = json.load(open(ground_truth_labels))
    all_results = {}

    for speaker_duration in tqdm.tqdm([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]):
        new_speaker_labels = rewrite_speakers(ground_truth_labels, speaker_duration)
        curr_path = args.whisper_initial_labels.replace(".json", f"_speaker_duration_{speaker_duration}.json")
        json.dump(new_speaker_labels, open(curr_path, "w"))
        print("Denoising Proportion Variations === ")
        speaker_results = auto_run_speaker(args.video_path, curr_path, denoise=True, denoise_prop=0.2, verification_threshold=0)
        speaker_results = speaker_results["segments"]
        evaluator = Evaluator(ground_truth_labels, speaker_results, None)
        results = evaluator.evaluate()
        all_results[speaker_duration] = results
    json.dump(all_results, open(args.output_path, "w"))