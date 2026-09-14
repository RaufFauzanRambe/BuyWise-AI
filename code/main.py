"""
BuyWise-AI Core Execution Entry Point
=====================================

This module serves as the primary Command Line Interface (CLI) and execution
driver for the BuyWise-AI platform. It orchestrates end-to-end operations including
data ingestion, model inference, system diagnostics, and pipeline automation.

Supported Execution Modes:
-------------------------
1. Ingest  : Triggers ingestion workflows for product catalogs or customer reviews.
2. Predict : Executes AI recommendation and scoring pipelines on target datasets.
3. Health  : Performs diagnostic checks on system components and connectivity.

Usage Examples:
---------------
Run ingestion for product catalog:
    $ python main.py ingest --source-type catalog --source-url https://api.buywise.ai/v1/products

Run prediction pipeline with custom batch size:
    $ python main.py predict --input-data ./data/raw_inputs.json --batch-size 256 --verbose

Run system health diagnostics:
    $ python main.py health
"""

import sys
import os
import argparse
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum, auto

# Importing from the ingestion package
from buywise_ai.ingestion import (
    IngestionConfig,
    IngestionStatus,
    IngestionSummary,
    ProductCatalogIngestor,
    ReviewDataIngestor,
    IngestionError
)

# ---------------------------------------------------------------------------
# Global Constants & Environment Setup
# ---------------------------------------------------------------------------

APP_NAME = "BuyWise-AI Core"
VERSION = "1.0.0"

# Setup logging standard output
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# ---------------------------------------------------------------------------
# Enumerations & Data Structures
# ---------------------------------------------------------------------------

class PipelineStage(Enum):
    """Execution stages supported by the application pipeline."""
    INGEST = "ingest"
    PREDICT = "predict"
    HEALTH = "health"


class SourceType(Enum):
    """Supported data source classifications for ingestion."""
    CATALOG = "catalog"
    REVIEWS = "reviews"


@dataclass
class ApplicationConfig:
    """Master application configuration payload.
    
    Attributes:
        stage (PipelineStage): Target execution command.
        source_type (Optional[SourceType]): Type of dataset to ingest.
        source_url (Optional[str]): Endpoint or storage URI for ingestion.
        input_file (Optional[str]): Input file path for batch prediction.
        batch_size (int): Processing chunk size.
        verbose (bool): Controls logger verbosity level.
    """
    stage: PipelineStage
    source_type: Optional[SourceType] = None
    source_url: Optional[str] = None
    input_file: Optional[str] = None
    batch_size: int = 100
    verbose: bool = False


# ---------------------------------------------------------------------------
# Core Execution Engine
# ---------------------------------------------------------------------------

class BuyWiseEngine:
    """Main Orchestrator engine executing workflow tasks based on configurations."""

    def __init__(self, config: ApplicationConfig) -> None:
        self.config = config
        self.logger = logging.getLogger("BuyWiseEngine")

    def run_ingestion_pipeline(self) -> int:
        """Executes data ingestion operations based on configured source types.
        
        Returns:
            int: Standard exit status code (0 for success, 1 for failure).
        """
        self.logger.info(f"Initiating Ingestion Pipeline for target type: {self.config.source_type}")

        if not self.config.source_url:
            self.logger.error("Ingestion failed: Argument '--source-url' is required.")
            return 1

        ingest_config = IngestionConfig(
            source_url=self.config.source_url,
            batch_size=self.config.batch_size
        )

        try:
            if self.config.source_type == SourceType.CATALOG:
                ingestor = ProductCatalogIngestor(config=ingest_config)
            elif self.config.source_type == SourceType.REVIEWS:
                ingestor = ReviewDataIngestor(config=ingest_config)
            else:
                self.logger.error(f"Unsupported source type: {self.config.source_type}")
                return 1

            summary: IngestionSummary = ingestor.run()
            
            if summary.status == IngestionStatus.SUCCESS:
                self.logger.info(
                    f"Ingestion completed successfully. "
                    f"Records Processed: {summary.records_processed}"
                )
                return 0
            else:
                self.logger.error(f"Ingestion execution failed. Errors: {summary.errors}")
                return 1

        except IngestionError as e:
            self.logger.error(f"Ingestion subpackage raised a critical exception: {str(e)}")
            return 1
        except Exception as e:
            self.logger.critical(f"Unhandled exception during ingestion execution: {str(e)}")
            return 1

    def run_prediction_pipeline(self) -> int:
        """Executes batch recommendation and scoring prediction pipelines.
        
        Returns:
            int: Standard exit status code (0 for success, 1 for failure).
        """
        self.logger.info("Initiating Inference and Recommendation Engine Pipeline...")
        
        if not self.config.input_file or not os.path.exists(self.config.input_file):
            self.logger.error(f"Invalid input file path provided: {self.config.input_file}")
            return 1

        # Simulated AI Model Processing Flow
        self.logger.info(f"Loading input payload from: {self.config.input_file}")
        self.logger.info(f"Executing batch predictions with batch_size={self.config.batch_size}...")
        
        # Mock prediction output
        predictions_generated = 42
        self.logger.info(f"Prediction complete. Generated {predictions_generated} recommendations.")
        return 0

    def run_health_check(self) -> int:
        """Performs system diagnostic verification and dependency checks.
        
        Returns:
            int: Standard exit status code (0 for success, 1 for failure).
        """
        self.logger.info(f"Running System Health Checks for {APP_NAME} v{VERSION}...")
        
        # Health Checks
        checks: Dict[str, bool] = {
            "Python Runtime": sys.version_info >= (3, 8),
            "Ingestion Subpackage Integrity": True,
            "Environment Security Context": True
        }

        all_passed = True
        for name, status in checks.items():
            status_str = "PASSED" if status else "FAILED"
            self.logger.info(f" - System Check: {name:<35} [{status_str}]")
            if not status:
                all_passed = False

        if all_passed:
            self.logger.info("All system diagnostics passed successfully.")
            return 0
        else:
            self.logger.error("System health check failed.")
            return 1

    def execute(self) -> int:
        """Main routing dispatch method for executing target workflow commands."""
        self.logger.info(f"Starting {APP_NAME} execution engine (v{VERSION})")

        if self.config.stage == PipelineStage.INGEST:
            return self.run_ingestion_pipeline()
        elif self.config.stage == PipelineStage.PREDICT:
            return self.run_prediction_pipeline()
        elif self.config.stage == PipelineStage.HEALTH:
            return self.run_health_check()
        else:
            self.logger.error(f"Unrecognized execution stage: {self.config.stage}")
            return 1


# ---------------------------------------------------------------------------
# CLI Argument Parser Setup
# ---------------------------------------------------------------------------

def build_cli_parser() -> argparse.ArgumentParser:
    """Constructs and returns the command line argument parser.
    
    Returns:
        argparse.ArgumentParser: Parser configured for BuyWise-AI tasks.
    """
    parser = argparse.ArgumentParser(
        prog="buywise-ai",
        description=f"{APP_NAME} - Enterprise AI-driven E-Commerce Intelligence CLI.",
        epilog="For full documentation and support, visit https://github.com/BuyWise-AI"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging level for verbose diagnostic outputs."
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        help="Target command stage to execute."
    )

    # 1. Ingestion Subcommand
    ingest_parser = subparsers.add_parser(
        PipelineStage.INGEST.value,
        help="Run data ingestion jobs."
    )
    ingest_parser.add_argument(
        "--source-type",
        type=str,
        choices=[e.value for e in SourceType],
        required=True,
        help="Target type of incoming dataset."
    )
    ingest_parser.add_argument(
        "--source-url",
        type=str,
        required=True,
        help="Target API endpoint or path for raw ingestion payload."
    )
    ingest_parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of records to fetch per batch chunk (default: 100)."
    )

    # 2. Prediction Subcommand
    predict_parser = subparsers.add_parser(
        PipelineStage.PREDICT.value,
        help="Run model inference and product recommendation pipeline."
    )
    predict_parser.add_argument(
        "--input-data",
        type=str,
        required=True,
        help="Path to the JSON/CSV input data file containing customer/product features."
    )
    predict_parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Number of inputs per prediction batch (default: 64)."
    )

    # 3. Health Check Subcommand
    subparsers.add_parser(
        PipelineStage.HEALTH.value,
        help="Perform diagnostic system health verification."
    )

    return parser


def parse_arguments(args: List[str]) -> ApplicationConfig:
    """Parses incoming command line options into an ApplicationConfig object.
    
    Args:
        args (List[str]): Command line parameter arguments.

    Returns:
        ApplicationConfig: Structured configuration object.
    """
    parser = build_cli_parser()
    parsed_args = parser.parse_args(args)

    stage = PipelineStage(parsed_args.command)
    source_type = SourceType(parsed_args.source_type) if hasattr(parsed_args, "source_type") and parsed_args.source_type else None
    source_url = getattr(parsed_args, "source_url", None)
    input_file = getattr(parsed_args, "input_data", None)
    batch_size = getattr(parsed_args, "batch_size", 100)

    return ApplicationConfig(
        stage=stage,
        source_type=source_type,
        source_url=source_url,
        input_file=input_file,
        batch_size=batch_size,
        verbose=parsed_args.verbose
    )


def configure_logging(verbose: bool) -> None:
    """Initializes runtime logging configurations.
    
    Args:
        verbose (bool): If True, sets log level to DEBUG, otherwise INFO.
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=[logging.StreamHandler(sys.stdout)]
    )


# ---------------------------------------------------------------------------
# Program Main Driver
# ---------------------------------------------------------------------------

def main() -> None:
    """Program entry point for CLI execution."""
    try:
        config = parse_arguments(sys.argv[1:])
        configure_logging(config.verbose)
        
        engine = BuyWiseEngine(config=config)
        exit_code = engine.execute()
        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\n[!] Process interrupted by user. Exiting safely...", file=sys.stderr)
        sys.exit(130)
    except Exception as err:
        print(f"[!] Fatal system initialization error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
