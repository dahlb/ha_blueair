# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/dahlb/ha_blueair/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                                        |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|---------------------------------------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| custom\_components/ha\_blueair/\_\_init\_\_.py                              |      161 |      135 |       26 |        0 |     14% |73-77, 95-207, 212-222, 227-229, 234-321, 326-338 |
| custom\_components/ha\_blueair/binary\_sensor.py                            |       31 |       31 |        2 |        0 |      0% |      3-94 |
| custom\_components/ha\_blueair/blueair\_update\_coordinator.py              |      201 |       17 |        0 |        0 |     92% |32-45, 58, 63, 88, 103, 113, 123, 296-297, 313-314 |
| custom\_components/ha\_blueair/blueair\_update\_coordinator\_device.py      |      194 |       85 |       22 |        0 |     50% |13-15, 24, 29, 34, 39, 44, 49, 54, 59, 64, 69-71, 76-81, 86-88, 93-95, 100-102, 107-109, 114-116, 121-123, 128-130, 135, 140-142, 152, 157, 162, 167, 172, 177, 182, 187, 192, 197, 202, 207, 212, 217, 222, 227, 232, 237, 242, 247, 252, 257, 262-263, 267, 271, 275, 279, 283, 287, 291, 295, 299, 303, 307, 311, 315, 319, 323, 327, 331, 335 |
| custom\_components/ha\_blueair/blueair\_update\_coordinator\_device\_aws.py |      277 |      147 |       30 |        0 |     42% |24, 29, 34, 44, 49, 54, 59, 64-69, 74-79, 84, 89, 94, 99-105, 110, 115, 124, 133, 138-140, 145-148, 153-156, 162-165, 170, 175, 180, 185, 190, 195-197, 202-204, 209-211, 216, 221, 226-230, 235, 240, 245-251, 256, 261, 266, 271, 276, 281, 286-292, 297, 302, 307-312, 317, 322, 327, 332, 336-337, 343-344, 348-353, 357-358, 362-363, 367-368, 372-373, 377-378, 382-383, 387-388, 392-393, 397-398, 402-410, 414-415, 419-420, 424-425, 429-430, 434-435, 439-440, 444-448, 452-453, 457-458, 462-463 |
| custom\_components/ha\_blueair/climate.py                                   |      280 |      145 |       96 |       16 |     43% |46, 49-50, 59, 69, 72-73, 77-81, 90, 137, 144, 148, 153, 157-159, 164, 169, 176, 179-180, 184, 187, 190-\>exit, 213-228, 243-251, 263, 266-267, 271, 275, 279-360, 364-403, 409, 411 |
| custom\_components/ha\_blueair/config\_flow.py                              |       46 |       25 |        6 |        0 |     40% |31, 46-50, 65, 69, 73-106 |
| custom\_components/ha\_blueair/const.py                                     |       29 |        0 |        0 |        0 |    100% |           |
| custom\_components/ha\_blueair/diagnostics.py                               |       39 |       39 |        8 |        0 |      0% |      3-83 |
| custom\_components/ha\_blueair/entity.py                                    |       44 |       15 |        8 |        0 |     63% |30-41, 52, 73-89 |
| custom\_components/ha\_blueair/fan.py                                       |      252 |      252 |      110 |        0 |      0% |     3-496 |
| custom\_components/ha\_blueair/humidifier.py                                |       93 |       93 |       12 |        0 |      0% |     3-192 |
| custom\_components/ha\_blueair/light.py                                     |      111 |      111 |       18 |        0 |      0% |     3-194 |
| custom\_components/ha\_blueair/mqtt\_mapping.py                             |        9 |        6 |        4 |        0 |     23% |     16-21 |
| custom\_components/ha\_blueair/sensor.py                                    |       80 |       80 |        8 |        0 |      0% |     3-351 |
| custom\_components/ha\_blueair/switch.py                                    |       33 |       33 |        0 |        0 |      0% |      3-88 |
| **TOTAL**                                                                   | **1880** | **1214** |  **350** |   **16** | **31%** |           |


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