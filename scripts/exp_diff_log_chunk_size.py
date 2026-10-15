#!/usr/bin/env python3
"""
Chunk Size Experiment Script for LogRoca

Tests different log chunk sizes with the 'simple' log_chunk_strategy.
Generates comprehensive Excel report with chunk-specific metrics.

Loop structure:
    for chunk_config in chunk_configs:  # OUTER LOOP
        for prompt_type in prompt_types:
            for retrieval_strategy in retrieval_strategies:
                run_test()
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
import traceback
import pandas as pd
from openpyxl.utils import get_column_letter

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.log_roca import LogRoca
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
log_base_path = Path(os.getenv("LOGROCA_ALSTOM_DATASET_PATH", "."))
log_exp_path = log_base_path / "logs" / "exp"

EXP_NUM = 7 # Will be increased when the experiement is repeated

RESULTS_DIR = Path(__file__).parent / "results" / f"exp-{EXP_NUM}"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Test configurations
PROMPT_TYPES = [
    # "one_shot", 
    # "zero_shot", 
    "zero_shot_cot", 
    # "one_shot_cot"
]
RETRIEVAL_STRATEGIES = [
    "exact_match", 
    # "semantic",
    # "hybrid"
]
LOG_CHUNK_STRATEGY = "simple"  # Fixed for this experiment

# CHUNK CONFIGS - Different sizes to test
CHUNK_CONFIGS = [
    {'size': 128, 'overlap': 20, 'name': 'tiny'},
    {'size': 256, 'overlap': 50, 'name': 'small'},
    {'size': 512, 'overlap': 100, 'name': 'medium'},
    {'size': 1024, 'overlap': 200, 'name': 'large'},
    # {'size': 2048, 'overlap': 400, 'name': 'xlarge'}, will be to big and if truncated might be lost
]

# Select log files to test
LOG_FILES = [
    log_exp_path / "log_0001.json",
    log_exp_path / "log_0002.json",
    log_exp_path / "log_0003.json",
    log_exp_path / "log_0004.json",
    log_exp_path / "log_0005.json",
    log_exp_path / "log_0006.json",
    log_exp_path / "log_0007.json",
    log_exp_path / "log_0008.json",
    log_exp_path / "log_0009.json",
    log_exp_path / "log_0010.json",
    log_exp_path / "log_0011.json",
    log_exp_path / "log_0012.json",
    log_exp_path / "log_0013.json",
    log_exp_path / "log_0014.json",
    log_exp_path / "log_0015.json",
    log_exp_path / "log_0016.json"
]

# LLM settings
LLM_MODEL = "deepseek-r1:1.5b"


def run_single_test(chunk_config, prompt_type, retrieval_strategy, log_file, temperature=0.1, experiment_counter=1):
    """
    Run a single test with specific configuration.

    Args:
        chunk_config: Dict with 'size', 'overlap', 'name'
        prompt_type: Prompt type to use
        retrieval_strategy: KB retrieval strategy
        log_file: Path to log file
        temperature: LLM temperature
        experiment_counter: Counter for experiment ID

    Returns:
        dict: Test results with metrics
    """
    chunk_name = chunk_config['name']
    test_name = f"{chunk_name}_{prompt_type}_{retrieval_strategy}"

    # Generate experiment ID: DLC_{number}
    experiment_id = f"DLC_{experiment_counter:04d}"

    print(f"\n{'='*80}")
    print(f"Experiment ID: {experiment_id}")
    print(f"Running test: {test_name}")
    print(f"  Chunk size: {chunk_config['size']} chars, overlap: {chunk_config['overlap']}")
    print(f"  Prompt: {prompt_type}")
    print(f"  Retrieval: {retrieval_strategy}")
    print(f"  Temperature: {temperature}")
    print(f"{'='*80}")

    start_time = time.time()

    try:
        # Initialize LogRoca with specific configuration
        log_roca = LogRoca(
            enable_phoenix=False,
            retrieval_strategy=retrieval_strategy,
            llm_model=LLM_MODEL,
            prompt_type=prompt_type,
            log_chunk_strategy=LOG_CHUNK_STRATEGY,
            temperature=temperature
        )

        # SET CHUNK CONFIGURATION (CRITICAL!)
        log_roca.set_log_chunk_config(
            chunk_size=chunk_config['size'],
            chunk_overlap=chunk_config['overlap']
        )

        # Get response
        response_json = log_roca.get_response(log_file)
        response = json.loads(response_json)

        # Get raw LLM output (before JSON parsing) for syntax validation
        raw_llm_output = log_roca.get_last_raw_llm_response()

        # Get metrics
        token_counts = log_roca.get_token_counts()
        rag_duration = log_roca.get_rag_duration()

        # Get context information
        log_chunks = log_roca.get_last_log_chunks()
        kb_chunks = log_roca.get_last_kb_chunks()

        # Get the ACTUAL truncated contexts sent to LLM (within budget)
        truncated_log_context = log_roca.get_last_truncated_log_context()
        truncated_kb_context = log_roca.get_last_truncated_kb_context()

        # Calculate chunk-specific metrics
        chunk_metrics = calculate_chunk_metrics(log_chunks)

        # Calculate truncation metrics
        truncation_metrics = calculate_truncation_metrics(
            token_counts,
            chunk_metrics.get('estimated_log_tokens', 0),
            len(kb_chunks)
        )

        # Get formatted prompt for validation
        formatted_prompt = log_roca.get_last_formatted_prompt()

        # Calculate actual token counts for truncated contexts (for analysis)
        # Use a simple estimation: 1 token ≈ 4 characters
        truncated_log_tokens = len(truncated_log_context) // 4 if truncated_log_context else 0
        truncated_kb_tokens = len(truncated_kb_context) // 4 if truncated_kb_context else 0
        full_prompt_tokens = len(formatted_prompt) // 4 if formatted_prompt else 0

        # Before truncation token counts (estimates)
        before_truncation_log_tokens = chunk_metrics.get('estimated_log_tokens', 0)
        before_truncation_kb_tokens = len(kb_chunks) * 300  # Rough estimate

        total_time = time.time() - start_time

        # Compile results
        result = {
            "experiment_id": experiment_id,
            "test_name": test_name,
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "chunk_size": chunk_config['size'],
                "chunk_overlap": chunk_config['overlap'],
                "chunk_name": chunk_name,
                "prompt_type": prompt_type,
                "log_chunk_strategy": LOG_CHUNK_STRATEGY,
                "retrieval_strategy": retrieval_strategy,
                "llm_model": LLM_MODEL,
                "temperature": temperature,
                "log_file": str(log_file.name)
            },
            "response": response,
            "metrics": {
                "total_time_seconds": round(total_time, 2),
                "rag_duration_seconds": round(rag_duration, 2),
                "token_counts": token_counts,
                "log_chunks_count": len(log_chunks),
                "kb_chunks_count": len(kb_chunks),
                "prompt_length_chars": len(formatted_prompt) if formatted_prompt else 0,
                **chunk_metrics,  # Add chunk-specific metrics
                **truncation_metrics,  # Add truncation metrics
                # Token counts for analysis
                "full_prompt_tokens": full_prompt_tokens,
                "before_truncation_kb_tokens": before_truncation_kb_tokens,
                "after_truncation_kb_tokens": truncated_kb_tokens,
                "before_truncation_log_tokens": before_truncation_log_tokens,
                "after_truncation_log_tokens": truncated_log_tokens,
            },
            # ANALYSIS DATA - Actual context sent to LLM (after truncation/budget constraints)
            # Use this to evaluate if LLM response makes sense given the actual context
            "analysis_data": {
                "truncated_log_context": truncated_log_context,  # Exact log content sent to LLM (within budget)
                "truncated_kb_context": truncated_kb_context,  # Exact KB content sent to LLM (within budget)
                "full_prompt": formatted_prompt,  # Complete final prompt sent to LLM
                "raw_llm_output": raw_llm_output,  # Raw LLM output before JSON parsing (for syntax validation)
                "llm_response": response  # LLM's parsed response for evaluation
            },
            "status": "success"
        }

        print(f"✓ Test completed successfully")
        print(f"  Duration: {total_time:.2f}s (RAG: {rag_duration:.2f}s)")
        print(f"  Tokens: {token_counts['total_input_tokens']} input, {token_counts['output_tokens']} output")
        print(f"  Chunks: {len(log_chunks)} log, {len(kb_chunks)} KB")
        print(f"  Avg chunk length: {chunk_metrics['avg_log_chunk_length']:.0f} chars")
        print(f"  Root cause: {response.get('root_cause', 'N/A')[:50]}...")
        print(f"  ✓ Saved analysis_data: raw LLM output + truncated contexts + full prompt")

        return result

    except Exception as e:
        total_time = time.time() - start_time
        error_msg = str(e)
        error_trace = traceback.format_exc()

        print(f"✗ Test failed: {error_msg}")

        result = {
            "experiment_id": experiment_id,
            "test_name": test_name,
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "chunk_size": chunk_config['size'],
                "chunk_overlap": chunk_config['overlap'],
                "chunk_name": chunk_name,
                "prompt_type": prompt_type,
                "log_chunk_strategy": LOG_CHUNK_STRATEGY,
                "retrieval_strategy": retrieval_strategy,
                "llm_model": LLM_MODEL,
                "temperature": temperature,
                "log_file": str(log_file.name)
            },
            "error": error_msg,
            "error_trace": error_trace,
            "metrics": {
                "total_time_seconds": round(total_time, 2)
            },
            "status": "failed"
        }

        return result


def calculate_chunk_metrics(log_chunks):
    """
    Calculate detailed metrics about log chunks.

    Args:
        log_chunks: List of log chunk strings

    Returns:
        dict: Chunk metrics
    """
    if not log_chunks:
        return {
            "avg_log_chunk_length": 0,
            "min_log_chunk_length": 0,
            "max_log_chunk_length": 0,
            "total_log_chunk_chars": 0,
            "estimated_log_tokens": 0,
        }

    chunk_lengths = [len(chunk) for chunk in log_chunks]
    total_chars = sum(chunk_lengths)

    # Estimate tokens (1 token ≈ 4 chars)
    estimated_tokens = total_chars // 4

    return {
        "avg_log_chunk_length": round(sum(chunk_lengths) / len(chunk_lengths), 2),
        "min_log_chunk_length": min(chunk_lengths),
        "max_log_chunk_length": max(chunk_lengths),
        "total_log_chunk_chars": total_chars,
        "estimated_log_tokens": estimated_tokens,
    }


def calculate_truncation_metrics(token_counts, estimated_log_tokens, kb_chunks_count):
    """
    Calculate truncation metrics for KB and log contexts.

    Args:
        token_counts: Token counts from LogRoca
        estimated_log_tokens: Estimated log tokens from chunks
        kb_chunks_count: Number of KB chunks retrieved

    Returns:
        dict: Truncation metrics
    """
    # Token budget calculations (based on LogRoca system)
    MAX_CONTEXT_WINDOW = 4000
    RESERVED_OUTPUT_TOKENS = 500
    MAX_INPUT_TOKENS = MAX_CONTEXT_WINDOW - RESERVED_OUTPUT_TOKENS  # 3500

    system_tokens = token_counts.get('system_prompt_tokens', 600)
    remaining_budget = MAX_INPUT_TOKENS - system_tokens  # ~2900

    kb_budget = int(remaining_budget * 0.6)  # 60% for KB (~1740 tokens)
    log_budget = int(remaining_budget * 0.4)  # 40% for log (~1160 tokens)

    # Estimate KB tokens (rough approximation: ~300 tokens per req/test case)
    estimated_kb_tokens = kb_chunks_count * 300

    # Calculate truncation for log context
    log_truncated = estimated_log_tokens > log_budget
    if log_truncated:
        log_truncation_pct = round(((estimated_log_tokens - log_budget) / estimated_log_tokens) * 100, 2)
    else:
        log_truncation_pct = 0.0

    # Calculate truncation for KB context
    kb_truncated = estimated_kb_tokens > kb_budget
    if kb_truncated:
        kb_truncation_pct = round(((estimated_kb_tokens - kb_budget) / estimated_kb_tokens) * 100, 2)
    else:
        kb_truncation_pct = 0.0

    return {
        "kb_budget_tokens": kb_budget,
        "log_budget_tokens": log_budget,
        "estimated_kb_tokens": estimated_kb_tokens,
        "kb_truncated": kb_truncated,
        "kb_truncation_pct": kb_truncation_pct,
        "log_truncated": log_truncated,
        "log_truncation_pct": log_truncation_pct,
    }


def run_all_tests(log_file, experiment_counter_start=1):
    """
    Run all test combinations.

    Loop structure:
        for chunk_config in CHUNK_CONFIGS:  # OUTER LOOP
            for prompt_type in PROMPT_TYPES:
                for retrieval_strategy in RETRIEVAL_STRATEGIES:
                    run_test()

    Args:
        log_file: Path to log file
        experiment_counter_start: Starting number for experiment IDs

    Returns:
        tuple: (all_results, next_counter) - Results list and next experiment counter
    """
    all_results = []

    total_tests = len(CHUNK_CONFIGS) * len(PROMPT_TYPES) * len(RETRIEVAL_STRATEGIES)
    current_test = 0
    experiment_counter = experiment_counter_start

    print(f"\n{'='*80}")
    print(f"Starting Chunk Size Experiment")
    print(f"Total tests to run: {total_tests}")
    print(f"Chunk configs: {len(CHUNK_CONFIGS)}")
    print(f"Prompt types: {len(PROMPT_TYPES)}")
    print(f"Retrieval strategies: {len(RETRIEVAL_STRATEGIES)}")
    print(f"{'='*80}\n")

    # OUTER LOOP: Chunk configurations
    for chunk_config in CHUNK_CONFIGS:
        chunk_name = chunk_config['name']
        print(f"\n{'#'*80}")
        print(f"# CHUNK CONFIG: {chunk_name} (size={chunk_config['size']}, overlap={chunk_config['overlap']})")
        print(f"{'#'*80}\n")

        for prompt_type in PROMPT_TYPES:
            # Adjust temperature for one-shot prompts to make LLM be more creative,
            # otherwise it will too strict to the example.
            if prompt_type == "one_shot" or prompt_type == "one_shot_cot":
                temperature = 0.7
            else:
                temperature = 0.0

            for retrieval_strategy in RETRIEVAL_STRATEGIES:
                current_test += 1
                print(f"\nProgress: {current_test}/{total_tests}")

                result = run_single_test(
                    chunk_config=chunk_config,
                    prompt_type=prompt_type,
                    retrieval_strategy=retrieval_strategy,
                    log_file=log_file,
                    temperature=temperature,
                    experiment_counter=experiment_counter
                )

                all_results.append(result)
                experiment_counter += 1

                # Save individual result with chunk name in filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                result_file = RESULTS_DIR / f"{result['test_name']}_{timestamp}.json"
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)

                # Small delay between tests
                time.sleep(1)

    return all_results, experiment_counter


def generate_summary_report(all_results):
    """
    Generate summary report from all test results.

    Args:
        all_results: List of all test results

    Returns:
        dict: Summary report
    """
    successful_tests = [r for r in all_results if r['status'] == 'success']
    failed_tests = [r for r in all_results if r['status'] == 'failed']

    summary = {
        "summary": {
            "total_tests": len(all_results),
            "successful": len(successful_tests),
            "failed": len(failed_tests),
            "success_rate": round(len(successful_tests) / len(all_results) * 100, 2) if all_results else 0,
            "log_files_processed": len(set(r['configuration']['log_file'] for r in successful_tests))
        },
        "test_configuration": {
            "prompt_types": PROMPT_TYPES,
            "chunk_configs": CHUNK_CONFIGS,
            "retrieval_strategies": RETRIEVAL_STRATEGIES,
            "log_chunk_strategy": LOG_CHUNK_STRATEGY,
            "llm_model": LLM_MODEL,
        },
        "results_by_chunk_size": {},
        "results_by_prompt": {},
        "results_by_retrieval": {}
    }

    # Group results by chunk size
    for chunk_config in CHUNK_CONFIGS:
        chunk_name = chunk_config['name']
        chunk_results = [r for r in successful_tests
                        if r['configuration']['chunk_name'] == chunk_name]

        if chunk_results:
            summary['results_by_chunk_size'][chunk_name] = {
                "chunk_size": chunk_config['size'],
                "chunk_overlap": chunk_config['overlap'],
                "test_count": len(chunk_results),
                "avg_rag_duration": round(sum(r['metrics']['rag_duration_seconds'] for r in chunk_results) / len(chunk_results), 2),
                "avg_total_tokens": round(sum(r['metrics']['token_counts']['total_input_tokens'] for r in chunk_results) / len(chunk_results), 2),
                "avg_log_chunks": round(sum(r['metrics']['log_chunks_count'] for r in chunk_results) / len(chunk_results), 2),
                "avg_chunk_length": round(sum(r['metrics']['avg_log_chunk_length'] for r in chunk_results) / len(chunk_results), 2),
                "avg_total_chars": round(sum(r['metrics']['total_log_chunk_chars'] for r in chunk_results) / len(chunk_results), 2),
            }

    # Group results by prompt type
    for prompt_type in PROMPT_TYPES:
        prompt_results = [r for r in successful_tests
                         if r['configuration']['prompt_type'] == prompt_type]

        if prompt_results:
            summary['results_by_prompt'][prompt_type] = {
                "test_count": len(prompt_results),
                "avg_rag_duration": round(sum(r['metrics']['rag_duration_seconds'] for r in prompt_results) / len(prompt_results), 2),
                "avg_total_tokens": round(sum(r['metrics']['token_counts']['total_input_tokens'] for r in prompt_results) / len(prompt_results), 2),
                "avg_log_chunks": round(sum(r['metrics']['log_chunks_count'] for r in prompt_results) / len(prompt_results), 2),
            }

    # Group results by retrieval strategy
    for retrieval_strategy in RETRIEVAL_STRATEGIES:
        retrieval_results = [r for r in successful_tests
                            if r['configuration']['retrieval_strategy'] == retrieval_strategy]

        if retrieval_results:
            summary['results_by_retrieval'][retrieval_strategy] = {
                "test_count": len(retrieval_results),
                "avg_rag_duration": round(sum(r['metrics']['rag_duration_seconds'] for r in retrieval_results) / len(retrieval_results), 2),
                "avg_total_tokens": round(sum(r['metrics']['token_counts']['total_input_tokens'] for r in retrieval_results) / len(retrieval_results), 2),
                "avg_kb_chunks": round(sum(r['metrics']['kb_chunks_count'] for r in retrieval_results) / len(retrieval_results), 2),
            }

    # Failed tests summary
    if failed_tests:
        summary['failed_tests'] = [
            {
                "test_name": r['test_name'],
                "error": r['error'],
                "configuration": r['configuration']
            }
            for r in failed_tests
        ]

    return summary


def generate_excel_report(all_results, summary, output_file):
    """
    Generate comprehensive Excel report with multiple sheets.

    Args:
        all_results: List of all test results
        summary: Summary report dictionary
        output_file: Path to output Excel file
    """
    print(f"\nGenerating Excel report: {output_file}")

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:

        # Sheet 1: All Results - Detailed view
        results_data = []
        for result in all_results:
            config = result['configuration']
            row = {
                'Experiment ID': result.get('experiment_id', 'N/A'),
                'Test Name': result['test_name'],
                'Timestamp': result['timestamp'],
                'Status': result['status'],
                'Log File': config['log_file'],
                'Chunk Name': config['chunk_name'],
                'Chunk Size': config['chunk_size'],
                'Chunk Overlap': config['chunk_overlap'],
                'Prompt Type': config['prompt_type'],
                'Retrieval Strategy': config['retrieval_strategy'],
                'Temperature': config['temperature'],
                'LLM Model': config['llm_model'],
            }

            if result['status'] == 'success':
                metrics = result['metrics']
                response = result['response']
                row.update({
                    'Total Time (s)': metrics['total_time_seconds'],
                    'RAG Duration (s)': metrics['rag_duration_seconds'],
                    'Input Tokens': metrics['token_counts']['total_input_tokens'],
                    'Output Tokens': metrics['token_counts']['output_tokens'],
                    'System Tokens': metrics['token_counts'].get('system_prompt_tokens', 0),
                    'Log Chunks Count': metrics['log_chunks_count'],
                    'KB Chunks Count': metrics['kb_chunks_count'],
                    'Avg Chunk Length': metrics.get('avg_log_chunk_length', 0),
                    'Min Chunk Length': metrics.get('min_log_chunk_length', 0),
                    'Max Chunk Length': metrics.get('max_log_chunk_length', 0),
                    'Total Chunk Chars': metrics.get('total_log_chunk_chars', 0),
                    'Estimated Tokens': metrics.get('estimated_log_tokens', 0),
                    'Prompt Length': metrics['prompt_length_chars'],
                    'Root Cause': response.get('root_cause', ''),
                    'Root Cause Origin': response.get('root_cause_origin', ''),
                    'Rationale': response.get('rationale', '')[:500],
                    'Action Suggestions': '; '.join(response.get('action_suggestions', [])),
                })
            else:
                row.update({
                    'Total Time (s)': result['metrics']['total_time_seconds'],
                    'Error': result.get('error', '')[:500],
                })

            results_data.append(row)

        df_all = pd.DataFrame(results_data)
        df_all.to_excel(writer, sheet_name='All Results', index=False)

        # Auto-adjust column widths (use get_column_letter for columns beyond Z)
        worksheet = writer.sheets['All Results']
        for idx, col in enumerate(df_all.columns):
            max_length = max(
                df_all[col].astype(str).apply(len).max(),
                len(col)
            )
            column_letter = get_column_letter(idx + 1)
            worksheet.column_dimensions[column_letter].width = min(max_length + 2, 50)

        # Sheet 2: Summary Statistics
        successful_results = [r for r in all_results if r['status'] == 'success']

        if successful_results:
            summary_data = {
                'Metric': [
                    'Total Tests',
                    'Successful Tests',
                    'Failed Tests',
                    'Success Rate (%)',
                    'Log Files Processed',
                    'Total Execution Time (min)',
                    'Avg RAG Duration (s)',
                    'Avg Input Tokens',
                    'Avg Output Tokens',
                    'Avg Log Chunks',
                    'Avg KB Chunks',
                    'Avg Chunk Length (chars)',
                ],
                'Value': [
                    len(all_results),
                    summary['summary']['successful'],
                    summary['summary']['failed'],
                    summary['summary']['success_rate'],
                    summary['summary']['log_files_processed'],
                    round(summary.get('execution_time_seconds', 0) / 60, 2),
                    round(sum(r['metrics']['rag_duration_seconds'] for r in successful_results) / len(successful_results), 2),
                    round(sum(r['metrics']['token_counts']['total_input_tokens'] for r in successful_results) / len(successful_results), 2),
                    round(sum(r['metrics']['token_counts']['output_tokens'] for r in successful_results) / len(successful_results), 2),
                    round(sum(r['metrics']['log_chunks_count'] for r in successful_results) / len(successful_results), 2),
                    round(sum(r['metrics']['kb_chunks_count'] for r in successful_results) / len(successful_results), 2),
                    round(sum(r['metrics'].get('avg_log_chunk_length', 0) for r in successful_results) / len(successful_results), 2),
                ]
            }
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='Summary', index=False)

        # Sheet 3: Chunk Size Comparison (KEY SHEET!)
        chunk_comparison_data = []
        for chunk_name, metrics in summary.get('results_by_chunk_size', {}).items():
            chunk_comparison_data.append({
                'Chunk Name': chunk_name,
                'Chunk Size (chars)': metrics['chunk_size'],
                'Chunk Overlap (chars)': metrics['chunk_overlap'],
                'Test Count': metrics['test_count'],
                'Avg RAG Duration (s)': metrics['avg_rag_duration'],
                'Avg Total Tokens': metrics['avg_total_tokens'],
                'Avg Log Chunks Created': metrics['avg_log_chunks'],
                'Avg Chunk Length (chars)': metrics['avg_chunk_length'],
                'Avg Total Chars': metrics['avg_total_chars'],
            })

        if chunk_comparison_data:
            df_chunk_comp = pd.DataFrame(chunk_comparison_data)
            # Sort by chunk size
            df_chunk_comp = df_chunk_comp.sort_values('Chunk Size (chars)')
            df_chunk_comp.to_excel(writer, sheet_name='Chunk Size Comparison', index=False)

        # Sheet 4: Chunk Size Details (per size breakdown)
        chunk_details_data = []
        for result in successful_results:
            chunk_details_data.append({
                'Experiment ID': result.get('experiment_id', 'N/A'),
                'Log File': result['configuration']['log_file'],
                'Chunk Name': result['configuration']['chunk_name'],
                'Chunk Size': result['configuration']['chunk_size'],
                'Prompt Type': result['configuration']['prompt_type'],
                'Retrieval': result['configuration']['retrieval_strategy'],
                'Chunks Created': result['metrics']['log_chunks_count'],
                'Avg Length': result['metrics'].get('avg_log_chunk_length', 0),
                'Min Length': result['metrics'].get('min_log_chunk_length', 0),
                'Max Length': result['metrics'].get('max_log_chunk_length', 0),
                'Total Chars': result['metrics'].get('total_log_chunk_chars', 0),
                'Estimated Tokens': result['metrics'].get('estimated_log_tokens', 0),
                'Input Tokens': result['metrics']['token_counts']['total_input_tokens'],
                'RAG Duration (s)': result['metrics']['rag_duration_seconds'],
            })

        if chunk_details_data:
            df_chunk_details = pd.DataFrame(chunk_details_data)
            df_chunk_details.to_excel(writer, sheet_name='Chunk Size Details', index=False)

        # Sheet 5: Token Budget Analysis
        token_budget_data = []
        MAX_LOG_BUDGET = 1160  # From your system (40% of ~2900)

        for result in successful_results:
            estimated_tokens = result['metrics'].get('estimated_log_tokens', 0)
            actual_input = result['metrics']['token_counts']['total_input_tokens']

            token_budget_data.append({
                'Experiment ID': result.get('experiment_id', 'N/A'),
                'Log File': result['configuration']['log_file'],
                'Chunk Name': result['configuration']['chunk_name'],
                'Chunk Size': result['configuration']['chunk_size'],
                'Test Name': result['test_name'],
                'Estimated Log Tokens': estimated_tokens,
                'Actual Input Tokens': actual_input,
                'Log Budget': MAX_LOG_BUDGET,
                'Over Budget?': 'Yes' if estimated_tokens > MAX_LOG_BUDGET else 'No',
                'Excess Tokens': max(0, estimated_tokens - MAX_LOG_BUDGET),
                'Budget Utilization %': round((estimated_tokens / MAX_LOG_BUDGET) * 100, 1),
            })

        if token_budget_data:
            df_budget = pd.DataFrame(token_budget_data)
            df_budget.to_excel(writer, sheet_name='Token Budget Analysis', index=False)

        # Sheet 6: Averages by Prompt Type
        prompt_avg_data = []
        for prompt_type, metrics in summary.get('results_by_prompt', {}).items():
            prompt_avg_data.append({
                'Prompt Type': prompt_type,
                'Test Count': metrics['test_count'],
                'Avg RAG Duration (s)': metrics['avg_rag_duration'],
                'Avg Total Tokens': metrics['avg_total_tokens'],
                'Avg Log Chunks': metrics['avg_log_chunks'],
            })

        if prompt_avg_data:
            df_prompt_avg = pd.DataFrame(prompt_avg_data)
            df_prompt_avg.to_excel(writer, sheet_name='Avg by Prompt Type', index=False)

        # Sheet 7: Averages by Retrieval Strategy
        retrieval_avg_data = []
        for retrieval_strategy, metrics in summary.get('results_by_retrieval', {}).items():
            retrieval_avg_data.append({
                'Retrieval Strategy': retrieval_strategy,
                'Test Count': metrics['test_count'],
                'Avg RAG Duration (s)': metrics['avg_rag_duration'],
                'Avg Total Tokens': metrics['avg_total_tokens'],
                'Avg KB Chunks': metrics['avg_kb_chunks'],
            })

        if retrieval_avg_data:
            df_retrieval_avg = pd.DataFrame(retrieval_avg_data)
            df_retrieval_avg.to_excel(writer, sheet_name='Avg by Retrieval', index=False)

        # Sheet 8: Truncation Analysis (NEW!)
        if successful_results:
            truncation_data = []
            for result in successful_results:
                metrics = result['metrics']
                truncation_data.append({
                    'Experiment ID': result.get('experiment_id', 'N/A'),
                    'Log File': result['configuration']['log_file'],
                    'Chunk Name': result['configuration']['chunk_name'],
                    'Chunk Size': result['configuration']['chunk_size'],
                    'Test Name': result['test_name'],
                    'KB Budget (tokens)': metrics.get('kb_budget_tokens', 0),
                    'Log Budget (tokens)': metrics.get('log_budget_tokens', 0),
                    'Estimated KB Tokens': metrics.get('estimated_kb_tokens', 0),
                    'Estimated Log Tokens': metrics.get('estimated_log_tokens', 0),
                    'KB Truncated?': 'Yes' if metrics.get('kb_truncated', False) else 'No',
                    'KB Truncation %': metrics.get('kb_truncation_pct', 0),
                    'Log Truncated?': 'Yes' if metrics.get('log_truncated', False) else 'No',
                    'Log Truncation %': metrics.get('log_truncation_pct', 0),
                })

            df_truncation = pd.DataFrame(truncation_data)
            df_truncation.to_excel(writer, sheet_name='Truncation Analysis', index=False)

        # Sheet 9: Root Cause Distribution
        if successful_results:
            root_cause_data = {}
            for result in successful_results:
                root_cause = result['response'].get('root_cause', 'unknown')
                if root_cause not in root_cause_data:
                    root_cause_data[root_cause] = 0
                root_cause_data[root_cause] += 1

            df_root_cause = pd.DataFrame([
                {'Root Cause': k, 'Count': v, 'Percentage': round(v / len(successful_results) * 100, 2)}
                for k, v in root_cause_data.items()
            ])
            df_root_cause = df_root_cause.sort_values('Count', ascending=False)
            df_root_cause.to_excel(writer, sheet_name='Root Cause Distribution', index=False)

        # Sheet 10: Context Token Analysis (NEW!)
        if successful_results:
            token_analysis_data = []
            for result in successful_results:
                metrics = result['metrics']
                token_analysis_data.append({
                    'Experiment ID': result.get('experiment_id', 'N/A'),
                    'Log File': result['configuration']['log_file'],
                    'Chunk Name': result['configuration']['chunk_name'],
                    'Chunk Size': result['configuration']['chunk_size'],
                    'Full Prompt Tokens': metrics.get('full_prompt_tokens', 0),
                    'KB Tokens (Before)': metrics.get('before_truncation_kb_tokens', 0),
                    'KB Tokens (After)': metrics.get('after_truncation_kb_tokens', 0),
                    'KB Truncated': 'Yes' if metrics.get('before_truncation_kb_tokens', 0) > metrics.get('after_truncation_kb_tokens', 0) else 'No',
                    'Log Tokens (Before)': metrics.get('before_truncation_log_tokens', 0),
                    'Log Tokens (After)': metrics.get('after_truncation_log_tokens', 0),
                    'Log Truncated': 'Yes' if metrics.get('before_truncation_log_tokens', 0) > metrics.get('after_truncation_log_tokens', 0) else 'No',
                })

            df_token_analysis = pd.DataFrame(token_analysis_data)
            df_token_analysis.to_excel(writer, sheet_name='Context Token Analysis', index=False)

        # Sheet 11: Analysis Data - Full Context for Manual Review (NEW!)
        if successful_results:
            analysis_sheet_data = []
            for result in successful_results:
                analysis_data = result.get('analysis_data', {})
                response = result['response']

                analysis_sheet_data.append({
                    'Experiment ID': result.get('experiment_id', 'N/A'),
                    'Log File': result['configuration']['log_file'],
                    'Root Cause': response.get('root_cause', ''),
                    'Root Cause Origin': response.get('root_cause_origin', ''),
                    'Action Suggestions': '\n'.join(response.get('action_suggestions', [])),
                    'Rationale': response.get('rationale', ''),
                    'Raw LLM Output': analysis_data.get('raw_llm_output', ''),
                    'Truncated KB Context': analysis_data.get('truncated_kb_context', ''),
                    'Truncated Log Context': analysis_data.get('truncated_log_context', ''),
                    'Final Prompt': analysis_data.get('full_prompt', ''),
                })

            df_analysis = pd.DataFrame(analysis_sheet_data)
            df_analysis.to_excel(writer, sheet_name='Analysis Data', index=False)

            # Auto-adjust column widths for Analysis Data sheet
            worksheet = writer.sheets['Analysis Data']
            for idx, col in enumerate(df_analysis.columns):
                # Set wider columns for text-heavy fields
                if col in ['Raw LLM Output', 'Truncated KB Context', 'Truncated Log Context', 'Final Prompt', 'Rationale']:
                    worksheet.column_dimensions[get_column_letter(idx + 1)].width = 80
                else:
                    max_length = min(max(
                        df_analysis[col].astype(str).apply(len).max(),
                        len(col)
                    ) + 2, 50)
                    worksheet.column_dimensions[get_column_letter(idx + 1)].width = max_length

        # Sheet 12: Failed Tests (if any)
        failed_results = [r for r in all_results if r['status'] == 'failed']
        if failed_results:
            failed_data = []
            for result in failed_results:
                failed_data.append({
                    'Experiment ID': result.get('experiment_id', 'N/A'),
                    'Test Name': result['test_name'],
                    'Log File': result['configuration']['log_file'],
                    'Chunk Name': result['configuration']['chunk_name'],
                    'Chunk Size': result['configuration']['chunk_size'],
                    'Prompt Type': result['configuration']['prompt_type'],
                    'Retrieval Strategy': result['configuration']['retrieval_strategy'],
                    'Error': result.get('error', '')[:1000],
                    'Timestamp': result['timestamp'],
                })

            df_failed = pd.DataFrame(failed_data)
            df_failed.to_excel(writer, sheet_name='Failed Tests', index=False)

    print(f"✓ Excel report generated with {len(writer.sheets)} sheets: {output_file}")
    print(f"  - Context Token Analysis: Before/after truncation token counts")
    print(f"  - Analysis Data: Full context + prompts + responses for manual review")


def main():
    """Main execution function."""
    print("\n" + "="*80)
    print(f"LogRoca Chunk Size Experiment number = {EXP_NUM}")
    print("Testing 'simple' log_chunk_strategy with different chunk sizes")
    print("="*80)

    print(f"\nLog files to process: {len(LOG_FILES)}")
    for i, lf in enumerate(LOG_FILES, 1):
        print(f"  {i}. {lf}")

    print(f"\nResults directory: {RESULTS_DIR}")
    print(f"LLM Model: {LLM_MODEL}")
    print(f"Log chunk strategy: {LOG_CHUNK_STRATEGY}")
    print(f"\nChunk configurations to test:")
    for config in CHUNK_CONFIGS:
        print(f"  - {config['name']}: size={config['size']}, overlap={config['overlap']}")

    # Run all tests for all log files
    start_time = time.time()
    all_results = []
    experiment_counter = 1

    for log_file in LOG_FILES:
        if not os.path.exists(log_file):
            print(f"\n⚠ Skipping missing log file: {log_file}")
            continue

        print(f"\nProcessing log file: {log_file}")
        results, experiment_counter = run_all_tests(log_file, experiment_counter)
        all_results.extend(results)

    total_time = time.time() - start_time

    # Generate summary
    summary = generate_summary_report(all_results)
    summary['execution_time_seconds'] = round(total_time, 2)
    summary['timestamp'] = datetime.now().isoformat()

    # Save summary
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    summary_file = RESULTS_DIR / f"chunk_size_summary_{timestamp}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # Save all results
    all_results_file = RESULTS_DIR / f"chunk_size_all_results_{timestamp}.json"
    with open(all_results_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    # Generate Excel report
    excel_file = RESULTS_DIR / f"chunk_size_experiment_{timestamp}.xlsx"
    generate_excel_report(all_results, summary, excel_file)

    # Print final summary
    print("\n" + "="*80)
    print("Chunk Size Experiment Complete")
    print("="*80)
    print(f"\nTotal execution time: {total_time/60:.2f} minutes")
    print(f"Total tests: {summary['summary']['total_tests']}")
    print(f"Successful: {summary['summary']['successful']} ({summary['summary']['success_rate']}%)")
    print(f"Failed: {summary['summary']['failed']}")
    print(f"Log files processed: {summary['summary']['log_files_processed']}")

    print(f"\nResults saved to:")
    print(f"  Summary JSON: {summary_file}")
    print(f"  All results JSON: {all_results_file}")
    print(f"  Excel Report: {excel_file}")
    print(f"  Individual results: {RESULTS_DIR}/")

    # Print chunk size comparison
    print("\n" + "-"*80)
    print("Chunk Size Comparison:")
    print("-"*80)
    for chunk_name, metrics in summary.get('results_by_chunk_size', {}).items():
        print(f"\n  {chunk_name.upper()} (size={metrics['chunk_size']}, overlap={metrics['chunk_overlap']}):")
        print(f"    Tests: {metrics['test_count']}")
        print(f"    Avg chunks created: {metrics['avg_log_chunks']:.1f}")
        print(f"    Avg chunk length: {metrics['avg_chunk_length']:.0f} chars")
        print(f"    Avg total chars: {metrics['avg_total_chars']:.0f}")
        print(f"    Avg RAG duration: {metrics['avg_rag_duration']:.2f}s")
        print(f"    Avg tokens: {metrics['avg_total_tokens']:.0f}")

    # Print failed tests if any
    if summary['summary']['failed'] > 0:
        print("\n\n⚠ Failed tests:")
        for failed in summary.get('failed_tests', []):
            print(f"\n  {failed['test_name']} (Log: {failed['configuration']['log_file']})")
            print(f"    Error: {failed['error'][:100]}...")

    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
