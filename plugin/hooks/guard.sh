#!/bin/sh
# Blocks raw mv/rm in protected filing areas through `aichivist guard`; silent until the aichivist CLI is installed.
command -v aichivist >/dev/null 2>&1 || exit 0
exec aichivist guard
