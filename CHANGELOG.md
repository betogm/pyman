# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2025-11-27

### Added
- **Enhanced URL Logging**: Logs now explicitly show both the "Original URL" (with `{{variables}}`) and the "Resolved URL".
- **Improved HTML Report**:
    - Request titles now display the script filename for easier identification.
    - The resolved URL is now displayed in the request summary line.
    - Both Original and Resolved URLs are included in the request details section.
    - Improved CSS styling for URL display.
    - **Layout Overhaul**: Redesigned the request summary to prominently display the script filename and its relative path.
    - **Copy Functionality**: Added copy-to-clipboard buttons for the script filename, full path, and request URL.
### Changed
- **CLI Behavior**: HTML report generation is now **enabled by default**.
- **New Flag**: Added `--no-report` flag to disable automatic HTML report generation.

## [0.2.0] - 2025-11-26

### Added
- **Structured JSON Reporting**: `pyman` now generates a `report_COLLECTION_TIMESTAMP.json` file containing detailed execution data (requests, responses, tests, errors).
- **Robust Error Detection**: Failures are now detected based on the internal execution state, independent of console log messages.
- **Improved HTML Report**: The HTML reporter now consumes the JSON report for 100% accuracy, falling back to log parsing only if necessary.
- **ErrorWatcherHandler**: A new internal logging handler to detect `ERROR` level logs even if exceptions are swallowed.

### Fixed
- Fixed an issue where swallowed exceptions in test scripts prevented failures from being reported in the summary and HTML report.
- Fixed `ColorFormatter` to correctly highlight custom failure messages in the console.

## [0.1.0] - 2025-11-18

### Added
- Initial release.
