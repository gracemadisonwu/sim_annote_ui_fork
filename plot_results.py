#!/usr/bin/env python3
"""
Script to plot diarization error rates and speaker classification F-1 scores
from the results folder.
"""

import json
import os
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import pandas as pd
import glob

if __name__ == "__main__":
    all_speaker_len_res = {"DER": {}, "F-1": {}}
    all_denoise_res = {"DER": {}, "F-1": {}}
    label_dict = {
        "original_video": "Single-channel #1",
        "neo_cam_video": "Single-channel #2",
        "nrp_episodes_video": "Single-channel #3"
    }
    for vname in ["original_video", "neo_cam_video", "nrp_episodes_video"]:
        speaker_len_res = json.load(open(f"results/{vname}/all_results_diff_speaker_lengths.json"))
        denoise_res = json.load(open(f"results/{vname}/all_results.json"))
        
        all_denoise_der = []
        all_denoise_f1 = []
        for k in denoise_res:
            all_denoise_der.append((float(k), denoise_res[k]["diarization"]))
            all_denoise_f1.append((float(k), denoise_res[k]["speaker_classification_f1"]["f1"]))
        
        all_denoise_res["DER"].update({
            label_dict[vname]: all_denoise_der
        })
        all_denoise_res["F-1"].update({
            label_dict[vname]: all_denoise_f1
        })
        
        all_speaker_der = []
        all_speaker_f1 = []
        for k in speaker_len_res:
            all_speaker_der.append((float(k), speaker_len_res[k]["diarization"]))
            all_speaker_f1.append((float(k), speaker_len_res[k]["speaker_classification_f1"]["f1"]))
        
        all_speaker_len_res["DER"].update({
            label_dict[vname]: all_speaker_der
        })
        all_speaker_len_res["F-1"].update({
            label_dict[vname]: all_speaker_f1
        })

    # Set seaborn style
    sns.set_style("whitegrid")
    sns.set_palette("husl")

    # Create figure with subplots for DER and F-1
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('VoxEmet Performance Metrics', fontsize=16, fontweight='bold')

    # Plot 1: DER vs Denoise Parameter (TOP LEFT)
    ax1 = axes[0, 0]
    for vname, data in all_denoise_res["DER"].items():
        df = pd.DataFrame(data, columns=['denoise_param', 'DER'])
        df = df.sort_values('denoise_param')
        sns.lineplot(data=df, x='denoise_param', y='DER', marker='o',
                     label=vname.replace('_', ' ').title(), ax=ax1, linewidth=2)
    ax1.set_xlabel('Denoise Proportion (0 - 1)', fontsize=12)
    ax1.set_ylabel('Diarization Error Rate (DER)', fontsize=12)
    ax1.set_title('DER vs Denoise Proportion', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Plot 2: F-1 vs Denoise Parameter (TOP RIGHT)
    ax2 = axes[0, 1]
    for vname, data in all_denoise_res["F-1"].items():
        df = pd.DataFrame(data, columns=['denoise_param', 'F1'])
        df = df.sort_values('denoise_param')
        sns.lineplot(data=df, x='denoise_param', y='F1', marker='o',
                     label=vname.replace('_', ' ').title(), ax=ax2, linewidth=2)
    ax2.set_xlabel('Denoise Proportion (0 - 1)', fontsize=12)
    ax2.set_ylabel('Speaker Classification F-1 Score', fontsize=12)
    ax2.set_title('F-1 Score vs Denoise Proportion', fontsize=14, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Plot 3: DER vs Speaker Length (BOTTOM LEFT)
    ax3 = axes[1, 0]
    for vname, data in all_speaker_len_res["DER"].items():
        df = pd.DataFrame(data, columns=['speaker_length', 'DER'])
        df = df.sort_values('speaker_length')
        sns.lineplot(data=df, x='speaker_length', y='DER', marker='o',
                     label=vname.replace('_', ' ').title(), ax=ax3, linewidth=2)
    ax3.set_xlabel('Seconds of Labelled Speech Provided (s)', fontsize=12)
    ax3.set_ylabel('Diarization Error Rate (DER)', fontsize=12)
    ax3.set_title('DER vs Seconds of Labelled Speech Provided', fontsize=14, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # Plot 4: F-1 vs Speaker Length (BOTTOM RIGHT)
    ax4 = axes[1, 1]
    for vname, data in all_speaker_len_res["F-1"].items():
        df = pd.DataFrame(data, columns=['speaker_length', 'F1'])
        df = df.sort_values('speaker_length')
        sns.lineplot(data=df, x='speaker_length', y='F1', marker='o',
                     label=vname.replace('_', ' ').title(), ax=ax4, linewidth=2)
    ax4.set_xlabel('Seconds of Labelled Speech Provided (s)', fontsize=12)
    ax4.set_ylabel('Speaker Classification F-1 Score', fontsize=12)
    ax4.set_title('F-1 Score vs Seconds of Labelled Speech Provided', fontsize=14, fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('results/performance_metrics.png', dpi=300, bbox_inches='tight')
    print("Plot saved to results/performance_metrics.png")
    plt.show()
