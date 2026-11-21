# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/dahlb/ha_blueair/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                       |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|----------------------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| custom\_components/ha\_blueair/\_\_init\_\_.py             |      162 |       84 |       24 |        3 |     44% |88-92, 117-219, 227-237, 262-263, 275, 284, 295, 314-326, 346-347 |
| custom\_components/ha\_blueair/binary\_sensor.py           |       31 |        7 |        2 |        0 |     73% |42, 49, 54, 81-83, 88 |
| custom\_components/ha\_blueair/climate.py                  |      279 |      144 |       96 |       16 |     43% |45, 48-49, 68, 71-72, 76-80, 89, 136, 143, 147, 152, 156-158, 163, 168, 175, 178-179, 183, 186, 189-\>exit, 212-227, 242-250, 262, 265-266, 270, 274, 278-359, 363-402, 408, 410 |
| custom\_components/ha\_blueair/config\_flow.py             |       52 |        0 |        6 |        0 |    100% |           |
| custom\_components/ha\_blueair/const.py                    |       26 |        0 |        0 |        0 |    100% |           |
| custom\_components/ha\_blueair/coordinator.py              |      201 |       17 |        0 |        0 |     92% |32-45, 58, 63, 88, 103, 113, 123, 296-297, 313-314 |
| custom\_components/ha\_blueair/coordinator\_device.py      |      194 |       85 |       22 |        0 |     50% |13-15, 24, 29, 34, 39, 44, 49, 54, 59, 64, 69-71, 76-81, 86-88, 93-95, 100-102, 107-109, 114-116, 121-123, 128-130, 135, 140-142, 152, 157, 162, 167, 172, 177, 182, 187, 192, 197, 202, 207, 212, 217, 222, 227, 232, 237, 242, 247, 252, 257, 262-263, 267, 271, 275, 279, 283, 287, 291, 295, 299, 303, 307, 311, 315, 319, 323, 327, 331, 335 |
| custom\_components/ha\_blueair/coordinator\_device\_aws.py |      268 |      135 |       24 |        0 |     46% |24, 29, 34, 44, 49, 54, 59, 64-69, 74-79, 84, 89, 94, 99-105, 110, 115, 124, 133, 138-140, 161, 166, 171, 176, 181, 186-188, 193-195, 200-202, 207, 212, 217-221, 226, 231, 236-242, 247, 252, 257, 262, 267, 272, 277-283, 288, 293, 298-303, 308, 313, 318, 323, 327-328, 334-335, 339-344, 348-349, 353-354, 358-359, 363-364, 368-369, 373-374, 378-379, 383-384, 388-389, 393-401, 405-406, 410-411, 415-416, 420-421, 425-426, 430-431, 435-439, 443-444, 448-449, 453-454 |
| custom\_components/ha\_blueair/diagnostics.py              |       35 |       35 |        8 |        0 |      0% |      3-77 |
| custom\_components/ha\_blueair/entity.py                   |       43 |       10 |        8 |        0 |     73% | 51, 76-92 |
| custom\_components/ha\_blueair/fan.py                      |      252 |      195 |      110 |        0 |     16% |65-67, 93, 97-110, 115, 120-122, 126-140, 144-148, 152-153, 162-172, 177, 182-186, 195, 212, 230, 234-278, 283, 288-327, 331-380, 384-428, 432-433, 442-464, 469, 474-496 |
| custom\_components/ha\_blueair/humidifier.py               |       93 |       50 |       12 |        0 |     41% |47, 54-61, 66-72, 77, 82, 87, 91-92, 101-102, 106-125, 133-135, 151, 155-157, 162, 167, 172, 176-177, 186-187, 191-192 |
| custom\_components/ha\_blueair/light.py                    |      111 |       56 |       18 |        0 |     43% |46, 50-65, 77, 81-82, 87-90, 95, 99-103, 107-108, 120, 124-125, 130-133, 138, 142-146, 150-151, 163, 167-168, 173-176, 181, 185-189, 193-194 |
| custom\_components/ha\_blueair/mqtt\_mapping.py            |        9 |        6 |        4 |        0 |     23% |     16-21 |
| custom\_components/ha\_blueair/sensor.py                   |       80 |       16 |        8 |        1 |     74% |81, 105, 112, 117, 122, 127, 282-284, 314-316, 344-346, 351 |
| custom\_components/ha\_blueair/switch.py                   |       33 |        7 |        0 |        0 |     79% |42, 46, 51, 55-56, 60-61 |
| **TOTAL**                                                  | **1869** |  **847** |  **342** |   **20** | **48%** |           |


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