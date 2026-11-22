# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/dahlb/ha_blueair/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                       |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|----------------------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| custom\_components/ha\_blueair/\_\_init\_\_.py             |      262 |        0 |       56 |        3 |     99% |315-\>317, 338-\>340, 534-\>552 |
| custom\_components/ha\_blueair/binary\_sensor.py           |       31 |        0 |        0 |        0 |    100% |           |
| custom\_components/ha\_blueair/climate.py                  |      285 |        0 |       96 |        5 |     99% |196-\>exit, 316-\>319, 359-\>exit, 390-\>393, 408-\>413 |
| custom\_components/ha\_blueair/config\_flow.py             |       82 |        0 |       14 |        0 |    100% |           |
| custom\_components/ha\_blueair/const.py                    |       29 |        0 |        0 |        0 |    100% |           |
| custom\_components/ha\_blueair/coordinator.py              |      223 |        1 |        2 |        1 |     99% |124-\>126, 206 |
| custom\_components/ha\_blueair/coordinator\_device.py      |      208 |        0 |       24 |        0 |    100% |           |
| custom\_components/ha\_blueair/coordinator\_device\_aws.py |      274 |        1 |       24 |        1 |     99% |       288 |
| custom\_components/ha\_blueair/diagnostics.py              |       50 |        0 |       18 |        2 |     97% |72-\>77, 87-\>120 |
| custom\_components/ha\_blueair/entity.py                   |       45 |        0 |        6 |        0 |    100% |           |
| custom\_components/ha\_blueair/fan.py                      |      247 |        0 |       96 |        9 |     97% |181-\>183, 299-\>301, 301-\>303, 306-\>308, 308-\>311, 372-\>374, 391-\>393, 452-\>454, 469-\>471 |
| custom\_components/ha\_blueair/humidifier.py               |       96 |        0 |       12 |        0 |    100% |           |
| custom\_components/ha\_blueair/light.py                    |      113 |        0 |       18 |        3 |     98% |94-\>96, 140-\>142, 186-\>188 |
| custom\_components/ha\_blueair/mqtt\_mapping.py            |        9 |        0 |        4 |        0 |    100% |           |
| custom\_components/ha\_blueair/sensor.py                   |       96 |        0 |        8 |        0 |    100% |           |
| custom\_components/ha\_blueair/switch.py                   |       39 |        0 |        0 |        0 |    100% |           |
| **TOTAL**                                                  | **2089** |    **2** |  **378** |   **24** | **99%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/dahlb/ha_blueair/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/dahlb/ha_blueair/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/dahlb/ha_blueair/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/dahlb/ha_blueair/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fdahlb%2Fha_blueair%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/dahlb/ha_blueair/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.