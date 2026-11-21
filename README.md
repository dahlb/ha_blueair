# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/dahlb/ha_blueair/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                       |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|----------------------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| custom\_components/ha\_blueair/\_\_init\_\_.py             |      160 |        1 |       24 |        3 |     98% |89, 217-\>219, 229-\>234 |
| custom\_components/ha\_blueair/binary\_sensor.py           |       32 |        0 |        2 |        0 |    100% |           |
| custom\_components/ha\_blueair/climate.py                  |      280 |        2 |       96 |        8 |     97% |192-\>exit, 215-\>220, 220-\>224, 229-230, 312-\>315, 349-\>exit, 380-\>383, 398-\>403 |
| custom\_components/ha\_blueair/config\_flow.py             |       69 |        0 |       12 |        1 |     99% | 101-\>103 |
| custom\_components/ha\_blueair/const.py                    |       26 |        0 |        0 |        0 |    100% |           |
| custom\_components/ha\_blueair/coordinator.py              |      220 |        2 |        2 |        1 |     99% |110-\>112, 155, 190 |
| custom\_components/ha\_blueair/coordinator\_device.py      |      198 |        1 |       22 |        1 |     99% |        15 |
| custom\_components/ha\_blueair/coordinator\_device\_aws.py |      268 |        1 |       24 |        1 |     99% |       279 |
| custom\_components/ha\_blueair/diagnostics.py              |       35 |        0 |        8 |        1 |     98% |   42-\>33 |
| custom\_components/ha\_blueair/entity.py                   |       43 |        0 |        8 |        0 |    100% |           |
| custom\_components/ha\_blueair/fan.py                      |      244 |        0 |      102 |        9 |     97% |145-\>147, 263-\>265, 265-\>267, 270-\>272, 272-\>275, 340-\>342, 360-\>362, 423-\>425, 440-\>442 |
| custom\_components/ha\_blueair/humidifier.py               |       94 |        1 |       12 |        1 |     98% |       128 |
| custom\_components/ha\_blueair/light.py                    |      112 |        0 |       18 |        3 |     98% |91-\>93, 134-\>136, 177-\>179 |
| custom\_components/ha\_blueair/mqtt\_mapping.py            |        9 |        0 |        4 |        0 |    100% |           |
| custom\_components/ha\_blueair/sensor.py                   |       81 |        0 |        8 |        0 |    100% |           |
| custom\_components/ha\_blueair/switch.py                   |       34 |        0 |        0 |        0 |    100% |           |
| **TOTAL**                                                  | **1905** |    **8** |  **342** |   **29** | **98%** |           |


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