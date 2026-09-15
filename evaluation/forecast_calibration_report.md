# Forecast Calibration Report

## Summary

- Total patterns analyzed: 250
- Requests with amount misses: 21

## Strategy Definitions

| Strategy | Description |
|----------|-------------|
| median | Median of recent (≤1yr or last 6) amounts — **current production** |
| most_recent | The most recent observed amount |
| mean | Arithmetic mean of recent amounts |
| ewma_0.3 | Exponentially weighted moving average (α=0.3) |
| trimmed_mean | Mean with min/max removed (when ≥4 observations) |

## Per-Request Pattern Detail

### request_02
- Expected amount: `17229139.2` | Status: `affordable_with_plan`
- User: `user_02`

| Category | Dir | N | Median | MostRecent | Mean | EWMA(0.3) | Trimmed |
|----------|-----|---|--------|------------|------|-----------|---------|
| salary | credit | 5 | 33345000.0 | 33345000.0 | 33345000.0 | 33345000.0 | 33345000.0 |
| housing | debit | 6 | 3534000.0 | 3534000.0 | 3534000.0 | 3534000.0 | 3534000.0 |
| utilities | debit | 5 | 2081730.85 | 2141849.94 | 2035830.5 | 2056649.68 | 2068394.13 |
| insurance | debit | 5 | 1132400.0 | 1132400.0 | 1132400.0 | 1132400.0 | 1132400.0 |
| education | debit | 5 | 3040000.0 | 3040000.0 | 3040000.0 | 3040000.0 | 3040000.0 |
| healthcare | debit | 5 | 1538498.1 | 1538498.1 | 1538993.97 | 1553742.12 | 1533632.0 |
| entertainment | debit | 5 | 1289187.4 | 1352563.79 | 1298171.69 | 1296005.75 | 1309793.16 |
| cloud_storage | debit | 5 | 369550.0 | 369550.0 | 369550.0 | 369550.0 | 369550.0 |
| groceries | debit | 18 | 1917086.28 | 1913686.86 | 1908881.3 | 2092700.51 | 1903963.79 |
| transport | debit | 13 | 1294200.86 | 1062310.27 | 1211967.94 | 1201440.42 | 1210875.96 |
| dining | debit | 9 | 1101709.76 | 1204805.34 | 1083819.45 | 1095882.53 | 1078195.58 |

**Amount history (recent):** `33345000.0|33345000.0|33345000.0|33345000.0|33345000.0`

**Analysis:** TODO — fill in after reviewing numbers.

### request_03
- Expected amount: `873000` | Status: `affordable_later`
- User: `user_03`

| Category | Dir | N | Median | MostRecent | Mean | EWMA(0.3) | Trimmed |
|----------|-----|---|--------|------------|------|-----------|---------|
| salary | credit | 6 | 4365000.0 | 1964250.0 | 3964875.0 | 3644775.0 | 4365000.0 |
| rent | debit | 5 | 1140000.0 | 1140000.0 | 1140000.0 | 1140000.0 | 1140000.0 |
| utilities | debit | 5 | 290684.15 | 262344.55 | 284387.81 | 282931.51 | 285517.36 |
| cloud_storage | debit | 5 | 20900.0 | 20900.0 | 20900.0 | 20900.0 | 20900.0 |
| streaming | debit | 5 | 117800.0 | 117800.0 | 117800.0 | 117800.0 | 117800.0 |
| shopping | debit | 5 | 173930.81 | 180395.29 | 168697.75 | 168528.52 | 169240.45 |
| groceries | debit | 18 | 184466.85 | 200238.72 | 193164.79 | 206032.59 | 193160.52 |
| transport | debit | 9 | 83523.33 | 106233.46 | 91041.06 | 94847.66 | 90180.01 |
| dining | debit | 9 | 146236.28 | 135718.35 | 149912.65 | 153381.87 | 150940.92 |

**Amount history (recent):** `4365000.0|4365000.0|4365000.0|4365000.0|4365000.0|1964250.0`

**Analysis:** TODO — fill in after reviewing numbers.

### request_04
- Expected amount: `8401800` | Status: `affordable_later`
- User: `user_04`

| Category | Dir | N | Median | MostRecent | Mean | EWMA(0.3) | Trimmed |
|----------|-----|---|--------|------------|------|-----------|---------|
| salary | credit | 6 | 38190000.0 | 38190000.0 | 33574744.05 | 34119344.25 | 38190000.0 |
| rent | debit | 6 | 12293000.0 | 12293000.0 | 12293000.0 | 12293000.0 | 12293000.0 |
| utilities | debit | 5 | 2004118.6 | 2004118.6 | 2003395.62 | 2004346.43 | 2000758.15 |
| music_subscription | debit | 5 | 332500.0 | 332500.0 | 332500.0 | 332500.0 | 332500.0 |
| delivery_membership | debit | 5 | 377150.0 | 377150.0 | 377150.0 | 377150.0 | 377150.0 |
| gym | debit | 5 | 1027900.0 | 1027900.0 | 1027900.0 | 1027900.0 | 1027900.0 |
| entertainment | debit | 5 | 1375854.05 | 1231859.39 | 1385201.35 | 1365469.27 | 1383842.46 |
| groceries | debit | 26 | 1468304.31 | 1433695.5 | 1499474.48 | 1525545.07 | 1503326.45 |
| transport | debit | 26 | 848248.97 | 1016425.58 | 832507.41 | 868043.83 | 834379.52 |
| dining | debit | 13 | 1839656.04 | 2108488.15 | 1748635.07 | 1807985.98 | 1760101.91 |

**Amount history (recent):** `38190000.0|38190000.0|38190000.0|10498464.28|38190000.0|38190000.0`

**Analysis:** TODO — fill in after reviewing numbers.

### request_05
- Expected amount: `737` | Status: `not_affordable`
- User: `user_05`

| Category | Dir | N | Median | MostRecent | Mean | EWMA(0.3) | Trimmed |
|----------|-----|---|--------|------------|------|-----------|---------|
| salary | credit | 5 | 14740.0 | 14740.0 | 14740.0 | 14740.0 | 14740.0 |
| rent | debit | 6 | 4972.0 | 4972.0 | 4972.0 | 4972.0 | 4972.0 |
| utilities | debit | 5 | 706.37 | 713.71 | 686.71 | 685.64 | 692.83 |
| debt_repayment | debit | 5 | 968.0 | 968.0 | 968.0 | 968.0 | 968.0 |
| healthcare | debit | 5 | 721.44 | 722.37 | 699.01 | 713.82 | 695.06 |
| family_support | debit | 5 | 840.4 | 840.4 | 840.4 | 840.4 | 840.4 |
| cloud_storage | debit | 5 | 113.3 | 113.3 | 113.3 | 113.3 | 113.3 |
| shopping | debit | 5 | 404.24 | 362.09 | 397.85 | 391.84 | 401.5 |
| groceries | debit | 26 | 741.58 | 720.51 | 721.7 | 712.02 | 724.81 |
| transport | debit | 13 | 411.47 | 388.74 | 414.34 | 390.01 | 415.57 |

**Amount history (recent):** `14740.0|14740.0|14740.0|14740.0|14740.0`

**Analysis:** TODO — fill in after reviewing numbers.

### request_06
- Expected amount: `603.3` | Status: `affordable_with_plan`
- User: `user_06`

| Category | Dir | N | Median | MostRecent | Mean | EWMA(0.3) | Trimmed |
|----------|-----|---|--------|------------|------|-----------|---------|
| salary | credit | 5 | 1441.0 | 1037.52 | 1279.61 | 1235.23 | 1306.51 |
| rent | debit | 5 | 254.1 | 254.1 | 254.1 | 254.1 | 254.1 |
| utilities | debit | 5 | 56.71 | 51.86 | 55.7 | 55.56 | 55.89 |
| insurance | debit | 5 | 26.0 | 26.0 | 26.0 | 26.0 | 26.0 |
| cloud_storage | debit | 5 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 |
| streaming | debit | 5 | 19.0 | 19.0 | 19.0 | 19.0 | 19.0 |
| shopping | debit | 5 | 39.88 | 39.88 | 41.0 | 40.45 | 40.26 |
| entertainment | debit | 5 | 35.1 | 38.33 | 35.01 | 35.39 | 34.88 |
| groceries | debit | 18 | 47.27 | 32.69 | 45.08 | 42.54 | 45.38 |
| transport | debit | 35 | 27.8 | 32.9 | 26.98 | 27.0 | 27.03 |
| dining | debit | 25 | 46.84 | 48.36 | 45.88 | 48.38 | 45.93 |

**Amount history (recent):** `1441.0|1441.0|1441.0|1037.52|1037.52`

**Analysis:** TODO — fill in after reviewing numbers.

### request_07
- Expected amount: `87170.56` | Status: `affordable_with_plan`
- User: `user_07`

| Category | Dir | N | Median | MostRecent | Mean | EWMA(0.3) | Trimmed |
|----------|-----|---|--------|------------|------|-----------|---------|
| salary | credit | 5 | 149000.0 | 149000.0 | 149000.0 | 149000.0 | 149000.0 |
| rent | debit | 6 | 34200.0 | 34200.0 | 34200.0 | 34200.0 | 34200.0 |
| utilities | debit | 5 | 7049.68 | 6209.57 | 6789.44 | 6684.65 | 6826.19 |
| debt_repayment | debit | 5 | 15650.0 | 15650.0 | 15650.0 | 15650.0 | 15650.0 |
| music_subscription | debit | 5 | 1005.0 | 1005.0 | 1005.0 | 1005.0 | 1005.0 |
| groceries | debit | 13 | 7280.22 | 5710.65 | 7116.46 | 6775.16 | 7133.41 |
| transport | debit | 9 | 3145.62 | 3145.62 | 3220.13 | 3263.07 | 3245.59 |
| dining | debit | 9 | 6313.91 | 6493.86 | 5927.31 | 6093.68 | 5998.28 |

**Amount history (recent):** `149000.0|149000.0|149000.0|149000.0|149000.0`

**Analysis:** TODO — fill in after reviewing numbers.

### request_08
- Expected amount: `284.57` | Status: `affordable_later`
- User: `user_08`

| Category | Dir | N | Median | MostRecent | Mean | EWMA(0.3) | Trimmed |
|----------|-----|---|--------|------------|------|-----------|---------|
| salary | credit | 5 | 1422.85 | 782.57 | 1294.79 | 1230.77 | 1422.85 |
| rent | debit | 6 | 467.5 | 467.5 | 467.5 | 467.5 | 467.5 |
| utilities | debit | 6 | 79.87 | 80.55 | 76.83 | 77.04 | 77.48 |
| education | debit | 5 | 89.0 | 89.0 | 89.0 | 89.0 | 89.0 |
| debt_repayment | debit | 5 | 177.0 | 177.0 | 177.0 | 177.0 | 177.0 |
| music_subscription | debit | 5 | 14.0 | 14.0 | 14.0 | 14.0 | 14.0 |
| delivery_membership | debit | 5 | 24.0 | 24.0 | 24.0 | 24.0 | 24.0 |
| groceries | debit | 26 | 54.69 | 72.38 | 59.04 | 60.89 | 58.78 |
| transport | debit | 26 | 37.31 | 47.21 | 37.49 | 37.39 | 37.53 |
| dining | debit | 13 | 49.45 | 42.33 | 50.84 | 49.08 | 50.8 |

**Amount history (recent):** `1422.85|1422.85|1422.85|1422.85|782.57`

**Analysis:** TODO — fill in after reviewing numbers.

### request_10
- Expected amount: `12700` | Status: `not_affordable`
- User: `user_10`

| Category | Dir | N | Median | MostRecent | Mean | EWMA(0.3) | Trimmed |
|----------|-----|---|--------|------------|------|-----------|---------|
| salary | credit | 21 | 65488.36 | 52239.8 | 64865.91 | 59035.31 | 65186.28 |
| rent | debit | 6 | 69100.0 | 69100.0 | 69100.0 | 69100.0 | 69100.0 |
| utilities | debit | 5 | 17538.11 | 17771.13 | 17103.95 | 17266.71 | 17019.33 |
| music_subscription | debit | 5 | 2800.0 | 2800.0 | 2800.0 | 2800.0 | 2800.0 |
| delivery_membership | debit | 5 | 1895.0 | 1895.0 | 1895.0 | 1895.0 | 1895.0 |
| gym | debit | 5 | 4860.0 | 4860.0 | 4860.0 | 4860.0 | 4860.0 |
| entertainment | debit | 5 | 4700.56 | 4883.78 | 4645.19 | 4682.0 | 4658.52 |
| groceries | debit | 26 | 10635.76 | 8011.08 | 10776.07 | 9352.43 | 10772.72 |
| transport | debit | 25 | 5776.08 | 6359.49 | 5982.79 | 5564.24 | 5984.55 |
| dining | debit | 13 | 8813.96 | 10370.83 | 8837.77 | 9191.99 | 8908.23 |

**Amount history (recent):** `74420.35|74852.29|54774.8|82410.47|72641.37|59553.07|65056.43|47245.98|81755.75|67741.04|79168.24|69351.86|78226.16|65488.36|60517.87|40977.52|60877.41|44415.5|47802.51|82667.27|52239.8`

**Analysis:** TODO — fill in after reviewing numbers.

### request_11
- Expected amount: `12510645` | Status: `affordable_with_plan`
- User: `user_11`

| Category | Dir | N | Median | MostRecent | Mean | EWMA(0.3) | Trimmed |
|----------|-----|---|--------|------------|------|-----------|---------|
| salary | credit | 10 | 21634053.23 | 8502888.2 | 18640837.88 | 17210294.82 | 19331186.32 |
| housing | debit | 5 | 2954500.0 | 2954500.0 | 2954500.0 | 2954500.0 | 2954500.0 |
| utilities | debit | 5 | 2796165.18 | 2796165.18 | 2720215.11 | 2727966.32 | 2732032.43 |
| insurance | debit | 5 | 1881000.0 | 1881000.0 | 1881000.0 | 1881000.0 | 1881000.0 |
| education | debit | 5 | 2544100.0 | 2544100.0 | 2544100.0 | 2544100.0 | 2544100.0 |
| healthcare | debit | 5 | 2973572.96 | 2826901.92 | 2943993.42 | 2903668.32 | 2972854.73 |
| entertainment | debit | 5 | 1649906.5 | 1674887.61 | 1600926.75 | 1593197.47 | 1637273.94 |
| cloud_storage | debit | 5 | 168150.0 | 168150.0 | 168150.0 | 168150.0 | 168150.0 |
| groceries | debit | 18 | 1400963.33 | 1341187.18 | 1421333.16 | 1354620.57 | 1422982.78 |
| transport | debit | 13 | 1185524.72 | 1244835.69 | 1088014.14 | 1164971.24 | 1095614.5 |
| dining | debit | 9 | 1365643.7 | 1163530.49 | 1350022.55 | 1312401.82 | 1347711.68 |

**Amount history (recent):** `23256000.0|16715584.16|23256000.0|8908379.93|23256000.0|15989420.0|23256000.0|20012106.46|23256000.0|8502888.2`

**Analysis:** TODO — fill in after reviewing numbers.

### request_13
- Expected amount: `433.4` | Status: `affordable_later`
- User: `user_13`

| Category | Dir | N | Median | MostRecent | Mean | EWMA(0.3) | Trimmed |
|----------|-----|---|--------|------------|------|-----------|---------|
| salary | credit | 10 | 1343.54 | 1343.54 | 1165.62 | 1220.91 | 1192.69 |
| rent | debit | 6 | 622.6 | 622.6 | 622.6 | 622.6 | 622.6 |
| utilities | debit | 6 | 143.54 | 134.25 | 143.66 | 141.76 | 141.92 |
| music_subscription | debit | 5 | 29.0 | 29.0 | 29.0 | 29.0 | 29.0 |
| delivery_membership | debit | 5 | 21.0 | 21.0 | 21.0 | 21.0 | 21.0 |
| gym | debit | 5 | 61.0 | 61.0 | 61.0 | 61.0 | 61.0 |
| entertainment | debit | 5 | 31.8 | 30.39 | 32.96 | 32.67 | 32.17 |
| groceries | debit | 26 | 100.05 | 93.66 | 99.66 | 96.41 | 99.86 |
| transport | debit | 26 | 45.33 | 37.29 | 44.83 | 43.58 | 44.73 |
| dining | debit | 13 | 62.71 | 61.28 | 64.27 | 58.37 | 64.29 |

**Amount history (recent):** `1343.54|993.88|1343.54|771.17|1343.54|948.46|1343.54|881.45|1343.54|1343.54`

**Analysis:** TODO — fill in after reviewing numbers.

### request_14
- Expected amount: `597.74` | Status: `not_affordable`
- User: `user_14`

| Category | Dir | N | Median | MostRecent | Mean | EWMA(0.3) | Trimmed |
|----------|-----|---|--------|------------|------|-----------|---------|
| salary | credit | 3 | 2717.0 | 2717.0 | 2717.0 | 2717.0 | 2717.0 |
| rent | debit | 6 | 688.6 | 688.6 | 688.6 | 688.6 | 688.6 |
| utilities | debit | 5 | 146.41 | 153.69 | 148.22 | 147.97 | 147.85 |
| debt_repayment | debit | 5 | 350.0 | 350.0 | 350.0 | 350.0 | 350.0 |
| healthcare | debit | 5 | 92.08 | 87.84 | 91.9 | 91.26 | 92.17 |
| family_support | debit | 5 | 226.0 | 226.0 | 226.0 | 226.0 | 226.0 |
| cloud_storage | debit | 5 | 14.0 | 14.0 | 14.0 | 14.0 | 14.0 |
| shopping | debit | 5 | 123.77 | 140.39 | 129.47 | 131.77 | 127.97 |
| groceries | debit | 26 | 99.0 | 129.56 | 104.8 | 109.21 | 104.29 |
| transport | debit | 13 | 52.26 | 43.88 | 51.06 | 49.57 | 51.26 |

**Amount history (recent):** `2717.0|2717.0|2717.0`

**Analysis:** TODO — fill in after reviewing numbers.

### request_15
- Expected amount: `83.05` | Status: `not_affordable`
- User: `user_15`

| Category | Dir | N | Median | MostRecent | Mean | EWMA(0.3) | Trimmed |
|----------|-----|---|--------|------------|------|-----------|---------|
| rent | debit | 6 | 435.6 | 435.6 | 435.6 | 435.6 | 435.6 |
| utilities | debit | 5 | 85.91 | 84.41 | 86.39 | 85.95 | 85.82 |
| education | debit | 5 | 159.0 | 159.0 | 159.0 | 159.0 | 159.0 |
| debt_repayment | debit | 5 | 84.0 | 84.0 | 84.0 | 84.0 | 84.0 |
| music_subscription | debit | 5 | 11.0 | 11.0 | 11.0 | 11.0 | 11.0 |
| delivery_membership | debit | 5 | 27.0 | 27.0 | 27.0 | 27.0 | 27.0 |
| salary | credit | 2 | 1661.0 | 1661.0 | 1661.0 | 1661.0 | 1661.0 |
| groceries | debit | 25 | 62.21 | 64.42 | 60.11 | 57.96 | 60.11 |
| transport | debit | 25 | 30.31 | 30.31 | 31.76 | 32.2 | 31.57 |
| dining | debit | 13 | 38.56 | 49.35 | 40.84 | 41.96 | 40.46 |

**Amount history (recent):** `435.6|435.6|435.6|435.6|435.6|435.6`

**Analysis:** TODO — fill in after reviewing numbers.

### request_17
- Expected amount: `243849.58` | Status: `affordable_with_plan`
- User: `user_17`

| Category | Dir | N | Median | MostRecent | Mean | EWMA(0.3) | Trimmed |
|----------|-----|---|--------|------------|------|-----------|---------|
| salary | credit | 6 | 206000.0 | 206000.0 | 206000.0 | 206000.0 | 206000.0 |
| rent | debit | 5 | 49600.0 | 49600.0 | 49600.0 | 49600.0 | 49600.0 |
| utilities | debit | 5 | 9530.77 | 8487.15 | 9538.75 | 9398.63 | 9653.35 |
| education | debit | 5 | 13660.0 | 13660.0 | 13660.0 | 13660.0 | 13660.0 |
| debt_repayment | debit | 5 | 30200.0 | 30200.0 | 30200.0 | 30200.0 | 30200.0 |
| music_subscription | debit | 5 | 2055.0 | 2055.0 | 2055.0 | 2055.0 | 2055.0 |
| delivery_membership | debit | 5 | 1675.0 | 1675.0 | 1675.0 | 1675.0 | 1675.0 |
| groceries | debit | 26 | 8677.53 | 8716.51 | 9096.7 | 9307.86 | 9098.93 |
| transport | debit | 26 | 5403.94 | 5372.15 | 5278.04 | 5263.32 | 5287.74 |
| dining | debit | 13 | 5641.06 | 4747.76 | 5777.68 | 5790.47 | 5804.09 |

**Amount history (recent):** `206000.0|206000.0|206000.0|206000.0|206000.0|206000.0`

**Analysis:** TODO — fill in after reviewing numbers.

### request_18
- Expected amount: `462` | Status: `affordable_later`
- User: `user_18`

| Category | Dir | N | Median | MostRecent | Mean | EWMA(0.3) | Trimmed |
|----------|-----|---|--------|------------|------|-----------|---------|
| salary | credit | 5 | 2310.0 | 2310.0 | 2310.0 | 2310.0 | 2310.0 |
| housing | debit | 6 | 167.0 | 167.0 | 167.0 | 167.0 | 167.0 |
| utilities | debit | 5 | 107.43 | 107.43 | 111.27 | 110.78 | 110.11 |
| insurance | debit | 5 | 68.0 | 68.0 | 68.0 | 68.0 | 68.0 |
| healthcare | debit | 5 | 152.41 | 147.96 | 155.41 | 155.75 | 155.0 |
| streaming | debit | 5 | 68.0 | 68.0 | 68.0 | 68.0 | 68.0 |
| groceries | debit | 18 | 95.32 | 111.41 | 93.42 | 97.03 | 93.86 |
| transport | debit | 13 | 43.81 | 43.81 | 43.85 | 43.49 | 43.7 |
| dining | debit | 13 | 82.67 | 101.88 | 85.63 | 88.14 | 85.58 |

**Amount history (recent):** `2310.0|2310.0|2310.0|2310.0|2310.0`

**Analysis:** TODO — fill in after reviewing numbers.

### request_19
- Expected amount: `28820` | Status: `affordable_with_plan`
- User: `user_19`

| Category | Dir | N | Median | MostRecent | Mean | EWMA(0.3) | Trimmed |
|----------|-----|---|--------|------------|------|-----------|---------|
| salary | credit | 5 | 131000.0 | 131000.0 | 131000.0 | 131000.0 | 131000.0 |
| rent | debit | 5 | 36100.0 | 36100.0 | 36100.0 | 36100.0 | 36100.0 |
| utilities | debit | 5 | 6029.9 | 6129.19 | 5955.64 | 6018.2 | 6037.03 |
| debt_repayment | debit | 5 | 11850.0 | 11850.0 | 11850.0 | 11850.0 | 11850.0 |
| healthcare | debit | 5 | 8645.36 | 8645.36 | 8808.57 | 8740.96 | 8695.93 |
| family_support | debit | 5 | 12650.0 | 12650.0 | 12650.0 | 12650.0 | 12650.0 |
| cloud_storage | debit | 5 | 395.0 | 395.0 | 395.0 | 395.0 | 395.0 |
| shopping | debit | 5 | 5772.78 | 5431.12 | 5833.87 | 5822.66 | 5811.85 |
| groceries | debit | 25 | 4744.13 | 4068.18 | 4772.82 | 4654.0 | 4773.44 |
| transport | debit | 13 | 3054.24 | 2765.93 | 3080.13 | 2863.84 | 3066.35 |

**Amount history (recent):** `131000.0|131000.0|131000.0|131000.0|131000.0`

**Analysis:** TODO — fill in after reviewing numbers.

### request_20
- Expected amount: `5400` | Status: `not_affordable`
- User: `user_20`

| Category | Dir | N | Median | MostRecent | Mean | EWMA(0.3) | Trimmed |
|----------|-----|---|--------|------------|------|-----------|---------|
| salary | credit | 5 | 108000.0 | 108000.0 | 108000.0 | 108000.0 | 108000.0 |
| housing | debit | 6 | 7950.0 | 7950.0 | 7950.0 | 7950.0 | 7950.0 |
| utilities | debit | 6 | 7777.08 | 7769.87 | 7665.16 | 7635.76 | 7770.9 |
| insurance | debit | 6 | 3290.0 | 3290.0 | 3290.0 | 3290.0 | 3290.0 |
| education | debit | 5 | 8740.0 | 8740.0 | 8740.0 | 8740.0 | 8740.0 |
| healthcare | debit | 5 | 6505.49 | 6654.33 | 6336.85 | 6347.98 | 6374.06 |
| entertainment | debit | 5 | 2115.92 | 2097.15 | 2148.27 | 2136.17 | 2164.25 |
| cloud_storage | debit | 5 | 365.0 | 365.0 | 365.0 | 365.0 | 365.0 |
| groceries | debit | 18 | 3713.32 | 4719.22 | 3700.53 | 3974.38 | 3692.38 |
| transport | debit | 13 | 2632.0 | 3243.84 | 2674.67 | 2998.86 | 2680.06 |
| dining | debit | 9 | 3352.75 | 3803.95 | 3423.79 | 3472.72 | 3410.85 |

**Amount history (recent):** `108000.0|108000.0|108000.0|108000.0|108000.0`

**Analysis:** TODO — fill in after reviewing numbers.

### request_21
- Expected amount: `1543.35` | Status: `affordable_with_plan`
- User: `user_21`

| Category | Dir | N | Median | MostRecent | Mean | EWMA(0.3) | Trimmed |
|----------|-----|---|--------|------------|------|-----------|---------|
| salary | credit | 6 | 2256.0 | 2256.0 | 2256.0 | 2256.0 | 2256.0 |
| rent | debit | 6 | 718.8 | 718.8 | 718.8 | 718.8 | 718.8 |
| utilities | debit | 5 | 122.18 | 124.08 | 121.18 | 121.03 | 122.16 |
| cloud_storage | debit | 5 | 11.0 | 11.0 | 11.0 | 11.0 | 11.0 |
| streaming | debit | 5 | 47.0 | 47.0 | 47.0 | 47.0 | 47.0 |
| shopping | debit | 5 | 120.74 | 126.38 | 122.41 | 123.91 | 120.99 |
| groceries | debit | 18 | 81.85 | 97.55 | 83.63 | 83.38 | 83.45 |
| transport | debit | 9 | 38.96 | 36.86 | 41.2 | 41.93 | 40.86 |
| dining | debit | 9 | 85.96 | 69.31 | 83.44 | 85.02 | 84.3 |

**Amount history (recent):** `2256.0|2256.0|2256.0|2256.0|2256.0|2256.0`

**Analysis:** TODO — fill in after reviewing numbers.

### request_22
- Expected amount: `475.46` | Status: `affordable_with_plan`
- User: `user_22`

| Category | Dir | N | Median | MostRecent | Mean | EWMA(0.3) | Trimmed |
|----------|-----|---|--------|------------|------|-----------|---------|
| salary | credit | 5 | 616.0 | 616.0 | 616.0 | 616.0 | 616.0 |
| rent | debit | 6 | 178.2 | 178.2 | 178.2 | 178.2 | 178.2 |
| utilities | debit | 5 | 31.52 | 27.34 | 30.56 | 29.93 | 30.58 |
| music_subscription | debit | 5 | 6.0 | 6.0 | 6.0 | 6.0 | 6.0 |
| delivery_membership | debit | 5 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 |
| gym | debit | 5 | 17.0 | 17.0 | 17.0 | 17.0 | 17.0 |
| entertainment | debit | 5 | 20.43 | 20.43 | 20.87 | 20.84 | 20.7 |
| groceries | debit | 26 | 23.43 | 26.82 | 23.95 | 22.85 | 23.94 |
| transport | debit | 25 | 12.7 | 15.02 | 13.13 | 14.51 | 13.14 |
| dining | debit | 13 | 15.84 | 18.41 | 16.07 | 16.39 | 15.99 |

**Amount history (recent):** `616.0|616.0|616.0|616.0|616.0`

**Analysis:** TODO — fill in after reviewing numbers.

### request_23
- Expected amount: `9152` | Status: `affordable_later`
- User: `user_23`

| Category | Dir | N | Median | MostRecent | Mean | EWMA(0.3) | Trimmed |
|----------|-----|---|--------|------------|------|-----------|---------|
| salary | credit | 5 | 45760.0 | 45760.0 | 45760.0 | 45760.0 | 45760.0 |
| rent | debit | 6 | 15312.0 | 15312.0 | 15312.0 | 15312.0 | 15312.0 |
| utilities | debit | 5 | 2813.94 | 2680.15 | 2754.39 | 2770.18 | 2790.65 |
| debt_repayment | debit | 5 | 5852.0 | 5852.0 | 5852.0 | 5852.0 | 5852.0 |
| healthcare | debit | 5 | 1341.05 | 1377.89 | 1361.55 | 1360.72 | 1350.05 |
| family_support | debit | 5 | 4270.2 | 4270.2 | 4270.2 | 4270.2 | 4270.2 |
| cloud_storage | debit | 5 | 295.9 | 295.9 | 295.9 | 295.9 | 295.9 |
| shopping | debit | 5 | 1281.33 | 1281.33 | 1315.73 | 1298.27 | 1316.7 |
| groceries | debit | 25 | 1706.85 | 1257.56 | 1732.48 | 1527.2 | 1732.45 |
| transport | debit | 13 | 896.02 | 783.18 | 888.44 | 878.96 | 885.95 |

**Amount history (recent):** `45760.0|45760.0|45760.0|45760.0|45760.0`

**Analysis:** TODO — fill in after reviewing numbers.

### request_24
- Expected amount: `13420` | Status: `not_affordable`
- User: `user_24`

| Category | Dir | N | Median | MostRecent | Mean | EWMA(0.3) | Trimmed |
|----------|-----|---|--------|------------|------|-----------|---------|
| salary | credit | 5 | 61000.0 | 61000.0 | 61000.0 | 61000.0 | 61000.0 |
| rent | debit | 6 | 18600.0 | 18600.0 | 18600.0 | 18600.0 | 18600.0 |
| utilities | debit | 5 | 3335.41 | 3490.5 | 3303.91 | 3314.22 | 3326.41 |
| insurance | debit | 6 | 2510.0 | 1830.0 | 2396.67 | 2306.0 | 2510.0 |
| cloud_storage | debit | 5 | 355.0 | 355.0 | 355.0 | 355.0 | 355.0 |
| streaming | debit | 5 | 1200.0 | 1200.0 | 1200.0 | 1200.0 | 1200.0 |
| shopping | debit | 5 | 2514.9 | 2564.0 | 2513.65 | 2504.4 | 2496.24 |
| entertainment | debit | 5 | 1896.25 | 1896.25 | 1930.7 | 1905.92 | 1894.34 |
| groceries | debit | 18 | 2248.73 | 2321.31 | 2290.43 | 2200.39 | 2277.79 |
| transport | debit | 36 | 1330.33 | 1593.41 | 1358.99 | 1385.42 | 1357.09 |
| dining | debit | 26 | 1902.53 | 1918.02 | 1854.04 | 1949.31 | 1859.39 |

**Amount history (recent):** `61000.0|61000.0|61000.0|61000.0|61000.0`

**Analysis:** TODO — fill in after reviewing numbers.

### request_25
- Expected amount: `1425000` | Status: `not_affordable`
- User: `user_25`

| Category | Dir | N | Median | MostRecent | Mean | EWMA(0.3) | Trimmed |
|----------|-----|---|--------|------------|------|-----------|---------|
| salary | credit | 6 | 28499994.0 | 28499994.000 | 28499994.0 | 28499994.0 | 28499994.0 |
| rent | debit | 6 | 6954000.0 | 6954000.0 | 6954000.0 | 6954000.0 | 6954000.0 |
| utilities | debit | 5 | 1338903.44 | 1201903.67 | 1323654.72 | 1304153.35 | 1338388.24 |
| insurance | debit | 5 | 904400.0 | 904400.0 | 904400.0 | 904400.0 | 904400.0 |
| cloud_storage | debit | 5 | 126350.0 | 126350.0 | 126350.0 | 126350.0 | 126350.0 |
| streaming | debit | 5 | 573800.0 | 573800.0 | 573800.0 | 573800.0 | 573800.0 |
| shopping | debit | 5 | 1054608.5 | 1170271.29 | 1059028.74 | 1070412.61 | 1052695.49 |
| entertainment | debit | 5 | 451681.59 | 426338.4 | 459592.42 | 458543.8 | 459176.74 |
| groceries | debit | 18 | 1231722.84 | 1472349.1 | 1199174.79 | 1246655.04 | 1200610.27 |
| transport | debit | 36 | 585491.54 | 571596.93 | 592511.15 | 604770.87 | 592321.58 |
| dining | debit | 25 | 1051249.87 | 1133036.68 | 1034677.39 | 1020738.45 | 1037599.03 |

**Amount history (recent):** `28499994.0|28499994.0|28499994.0|28499994.0|28499994.0|28499994.0`

**Analysis:** TODO — fill in after reviewing numbers.

## Conclusion

_To be filled after reviewing per-request analysis._

**Recommended strategy:** 

**Expected improvement:** 