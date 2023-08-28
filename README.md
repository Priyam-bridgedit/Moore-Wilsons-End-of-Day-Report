# End of Day Reports

Automated End of Day Reports Tool for Moore Wilsons. This project enables users to view and modify transaction reports for a specific branch, date, and lane. Additionally, it provides a summary of all lanes' data for a given branch and date.

## Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [How to Build the Executable](#how-to-build-the-executable)
- [Contact](#contact)

## Introduction

The End of Day Reports tool is designed to streamline the process of handling daily transaction reports for Moore Wilsons. It empowers users to review and adjust reported amounts for specific branches, dates, and lanes. Furthermore, the tool provides summarized data for all lanes of a particular branch and date.

## Features

- View and modify transaction reports for a specific branch, date, and lane.
- Save modified data to the 'MW_EOD' app database.
- Generate a summary of all lanes' data for a given branch and date.

## Installation

Follow these steps to set up the End of Day Reports tool:

1. Clone this repository to your local machine:

```bash
$ git clone https://github.com/Priyam-bridgedit/Moore-Wilsons-End-of-Day-Report.git
$ cd Moore-Wilsons-End-of-Day-Report
Install the required dependencies:
bash
$ pip install -r requirements.txt
Usage
To use the End of Day Reports tool:



Configuration
Customize the tool's behavior by adjusting settings in the config.ini file. This includes database connections, app settings, and any other relevant parameters.

How to Build the Executable
To create a standalone executable from the Python code:

Open a terminal and navigate to the location of setup.py:
bash
$ cd /path/to/end-of-day-reports
Build the executable using the following command:
bash
$ python setup.py build
The resulting executable will be located in the build directory.


License
This project is licensed under the MIT License.

Contact
For questions or further information, feel free to reach out to us at priyampatel704@gmail.com.
