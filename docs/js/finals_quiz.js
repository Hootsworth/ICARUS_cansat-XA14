/**
 * ICARUS Finals Quiz — 5 unique question sets for the top 5 finalist teams.
 * Each slot has 7 MCQ questions worth 15 PTS each (max 105 PTS).
 * Admin assigns teams to slots via the Finalist Selector panel.
 */

window.ICARUS_FINALS_QUESTIONS = {

    // =========================================================================
    // SLOT 1 — Finalist Position #1
    // =========================================================================
    slot1: [
        {
            id: "q1",
            category: "PYTHON FUNDAMENTALS",
            question: "```python\nx = [1, 2, 3]\nprint(x[::-1])\n```\nWhat is the output?",
            options: [
                { key: "A", text: "[1, 2, 3]" },
                { key: "B", text: "[3, 2, 1]" },
                { key: "C", text: "[3, 2]" },
                { key: "D", text: "Error" }
            ],
            answer: "B"
        },
        {
            id: "q2",
            category: "SENSOR ANALYSIS",
            question: "A sensor normally has noise of about ±0.2 units. One reading differs from the expected value by 0.3 units.\n\nWhat is the best conclusion?",
            options: [
                { key: "A", text: "Definitely a sensor failure" },
                { key: "B", text: "Definitely a real event" },
                { key: "C", text: "Not enough evidence from that reading alone" },
                { key: "D", text: "The reading must be deleted" }
            ],
            answer: "C"
        },
        {
            id: "q3",
            category: "CORRELATION ANALYSIS",
            question: "Two variables have correlation 0.91. After randomly shuffling one variable's values, the correlation becomes 0.03.\n\nWhat does this most strongly suggest?",
            options: [
                { key: "A", text: "The original relationship was likely meaningful" },
                { key: "B", text: "Correlation cannot be calculated correctly" },
                { key: "C", text: "The shuffled data is more accurate" },
                { key: "D", text: "The variables are causally related" }
            ],
            answer: "A"
        },
        {
            id: "q4",
            category: "SIGNAL PATTERN RECOGNITION",
            question: "A telemetry signal is:\n\n4.9, 5.0, 5.1, 5.0, 5.1, 7.8, 7.9, 8.0, 7.9\n\nWhich description fits best?",
            options: [
                { key: "A", text: "Isolated spike" },
                { key: "B", text: "Sustained level shift" },
                { key: "C", text: "Random missing data" },
                { key: "D", text: "Gradual drift from the beginning" }
            ],
            answer: "B"
        },
        {
            id: "q5",
            category: "DATA PROCESSING",
            question: "```python\ndf[\"altitude\"].rolling(5).mean()\n```\nCompared with the original altitude signal, the rolling mean will generally:",
            options: [
                { key: "A", text: "Increase the noise" },
                { key: "B", text: "Smooth short-term fluctuations" },
                { key: "C", text: "Guarantee anomaly removal" },
                { key: "D", text: "Preserve every sudden spike exactly" }
            ],
            answer: "B"
        },
        {
            id: "q6",
            category: "MULTI-SENSOR INTERPRETATION",
            question: "A parachute deploys at 450 m. Immediately afterward:\n\n• descent rate increases\n• pressure increases\n• acceleration changes\n• GPS remains continuous\n\nWhat is the strongest interpretation?",
            options: [
                { key: "A", text: "Multiple independent signals support a real state transition" },
                { key: "B", text: "The pressure sensor is definitely faulty" },
                { key: "C", text: "GPS should be discarded" },
                { key: "D", text: "The event is necessarily an anomaly" }
            ],
            answer: "A"
        },
        {
            id: "q7",
            category: "ANOMALY RATES",
            question: "A dataset contains 1 million readings and one impossible value. Another dataset contains 100 readings and ten suspicious values.\n\nWhich has the higher anomaly rate?",
            options: [
                { key: "A", text: "First dataset" },
                { key: "B", text: "Second dataset" },
                { key: "C", text: "Both are 1%" },
                { key: "D", text: "Cannot calculate without the mean" }
            ],
            answer: "B"
        }
    ],

    // =========================================================================
    // SLOT 2 — Finalist Position #2
    // =========================================================================
    slot2: [
        {
            id: "q1",
            category: "PYTHON FUNDAMENTALS",
            question: "```python\nx = [10, 20, 30]\nprint(x[-1] - x[0])\n```\nWhat is the output?",
            options: [
                { key: "A", text: "10" },
                { key: "B", text: "20" },
                { key: "C", text: "30" },
                { key: "D", text: "40" }
            ],
            answer: "B"
        },
        {
            id: "q2",
            category: "SIGNAL PATTERN RECOGNITION",
            question: "A temperature signal rises slowly for 3 minutes and then suddenly returns to its previous level.\n\nWhich pattern is most consistent with this?",
            options: [
                { key: "A", text: "Single-point spike" },
                { key: "B", text: "Temporary drift" },
                { key: "C", text: "Permanent calibration change" },
                { key: "D", text: "Duplicate timestamp" }
            ],
            answer: "B"
        },
        {
            id: "q3",
            category: "STATISTICAL REASONING",
            question: "You calculate the mean battery voltage and get 7.4V.\n\nWhat information does this NOT tell you?",
            options: [
                { key: "A", text: "Central tendency" },
                { key: "B", text: "Exact minimum voltage" },
                { key: "C", text: "Average voltage" },
                { key: "D", text: "Approximate typical level" }
            ],
            answer: "B"
        },
        {
            id: "q4",
            category: "DIAGNOSTIC REASONING",
            question: "A GPS coordinate suddenly moves 2 km, but altitude, pressure, velocity, and acceleration remain completely consistent with the previous trajectory.\n\nWhat should be investigated first?",
            options: [
                { key: "A", text: "GPS specifically" },
                { key: "B", text: "Every sensor equally" },
                { key: "C", text: "Battery chemistry" },
                { key: "D", text: "Parachute deployment" }
            ],
            answer: "A"
        },
        {
            id: "q5",
            category: "PANDAS / DATA QUALITY",
            question: "```python\ndf[\"temperature\"].isna().mean()\n```\nIf the result is 0.04, what does that mean?",
            options: [
                { key: "A", text: "4 missing values" },
                { key: "B", text: "4% of temperature entries are missing" },
                { key: "C", text: "Temperature averages 0.04" },
                { key: "D", text: "0.04 values are missing" }
            ],
            answer: "B"
        },
        {
            id: "q6",
            category: "OUTLIER ASSESSMENT",
            question: "A sensor has readings:\n\n10, 10, 10, 10, 50\n\nWhich statement is most defensible?",
            options: [
                { key: "A", text: "50 is automatically an error" },
                { key: "B", text: "50 is automatically a real event" },
                { key: "C", text: "50 is unusual and needs contextual investigation" },
                { key: "D", text: "The mean proves 50 is correct" }
            ],
            answer: "C"
        },
        {
            id: "q7",
            category: "EVIDENCE STRENGTHENING",
            question: "You observe that battery voltage decreases whenever current increases.\n\nWhat additional evidence would best strengthen the claim that current draw is related to battery voltage drop?",
            options: [
                { key: "A", text: "More observations across different flight conditions" },
                { key: "B", text: "A larger font on the graph" },
                { key: "C", text: "Removing all low-voltage readings" },
                { key: "D", text: "Changing the timestamp format" }
            ],
            answer: "A"
        }
    ],

    // =========================================================================
    // SLOT 3 — Finalist Position #3
    // =========================================================================
    slot3: [
        {
            id: "q1",
            category: "PYTHON FUNDAMENTALS",
            question: "```python\nx = [1, 2, 3]\ny = x\ny = y + [4]\nprint(x)\n```\nWhat is the output?",
            options: [
                { key: "A", text: "[1, 2, 3]" },
                { key: "B", text: "[1, 2, 3, 4]" },
                { key: "C", text: "[4]" },
                { key: "D", text: "Error" }
            ],
            answer: "A"
        },
        {
            id: "q2",
            category: "TREND ANALYSIS",
            question: "A graph shows altitude decreasing almost linearly, but vertical velocity is noisy and alternates between positive and negative values.\n\nWhich should you trust more for identifying the overall descent trend?",
            options: [
                { key: "A", text: "One noisy velocity reading" },
                { key: "B", text: "The consistent altitude trend" },
                { key: "C", text: "The maximum velocity only" },
                { key: "D", text: "Neither can provide information" }
            ],
            answer: "B"
        },
        {
            id: "q3",
            category: "SYSTEMATIC ERRORS",
            question: "Two sensors measuring the same physical quantity disagree by a constant amount throughout the flight.\n\nWhat is the most plausible explanation?",
            options: [
                { key: "A", text: "Random noise only" },
                { key: "B", text: "Possible systematic offset/bias" },
                { key: "C", text: "Guaranteed sensor failure" },
                { key: "D", text: "Perfect agreement" }
            ],
            answer: "B"
        },
        {
            id: "q4",
            category: "DATA QUALITY",
            question: "A dataset has timestamps:\n\n0, 1, 2, 3, 8, 9, 10\n\nWhat is immediately suspicious?",
            options: [
                { key: "A", text: "The values are increasing" },
                { key: "B", text: "There is a gap in sampling between 3 and 8" },
                { key: "C", text: "There are seven readings" },
                { key: "D", text: "The first timestamp is zero" }
            ],
            answer: "B"
        },
        {
            id: "q5",
            category: "ANOMALY LOGIC",
            question: "A model flags an observation as anomalous because it is statistically rare.\n\nWhich statement is correct?",
            options: [
                { key: "A", text: "Rare means physically impossible" },
                { key: "B", text: "Rare means faulty" },
                { key: "C", text: "Rare means worth investigating" },
                { key: "D", text: "Rare means it must be deleted" }
            ],
            answer: "C"
        },
        {
            id: "q6",
            category: "CORRELATION EDGE CASE",
            question: "Suppose altitude and pressure have correlation -0.97.\n\nDuring a short section of flight, altitude decreases but pressure also decreases.\n\nWhat is the best interpretation?",
            options: [
                { key: "A", text: "The correlation guarantees pressure must increase" },
                { key: "B", text: "The short section may represent an unusual event or measurement issue" },
                { key: "C", text: "The entire dataset is invalid" },
                { key: "D", text: "Correlation cannot be negative" }
            ],
            answer: "B"
        },
        {
            id: "q7",
            category: "METHOD COMPARISON",
            question: "You have two anomaly-detection methods.\n\nMethod A flags 2% of readings.\nMethod B flags 18%.\n\nWithout knowing anything else, which is better?",
            options: [
                { key: "A", text: "A" },
                { key: "B", text: "B" },
                { key: "C", text: "Cannot determine" },
                { key: "D", text: "The one with more anomalies" }
            ],
            answer: "C"
        }
    ],

    // =========================================================================
    // SLOT 4 — Finalist Position #4
    // =========================================================================
    slot4: [
        {
            id: "q1",
            category: "PYTHON FUNDAMENTALS",
            question: "```python\na = [1, 2, 3]\nb = a.copy()\nb[0] = 99\n```\nWhat is `a`?",
            options: [
                { key: "A", text: "[99, 2, 3]" },
                { key: "B", text: "[1, 2, 3]" },
                { key: "C", text: "[99]" },
                { key: "D", text: "Error" }
            ],
            answer: "B"
        },
        {
            id: "q2",
            category: "VARIABILITY ANALYSIS",
            question: "A sensor's readings are:\n\n20.0, 20.1, 20.0, 20.1, 20.0\n\nAfter an event they become:\n\n20.0, 21.5, 19.2, 21.7, 19.0\n\nWhat changed most clearly?",
            options: [
                { key: "A", text: "Mean necessarily increased" },
                { key: "B", text: "Variability increased" },
                { key: "C", text: "Sampling stopped" },
                { key: "D", text: "The sensor became perfectly stable" }
            ],
            answer: "B"
        },
        {
            id: "q3",
            category: "MULTI-SENSOR EVENTS",
            question: "A sudden spike appears in temperature, battery, and current at exactly the same timestamp.\n\nCompared with a spike in temperature alone, this is:",
            options: [
                { key: "A", text: "More suggestive of a system-wide event" },
                { key: "B", text: "Less suspicious by definition" },
                { key: "C", text: "Proof that all three sensors are faulty" },
                { key: "D", text: "Impossible in real telemetry" }
            ],
            answer: "A"
        },
        {
            id: "q4",
            category: "PANDAS INDEX",
            question: "```python\ndf[\"battery\"].idxmin()\n```\nreturns 127.\n\nWhat does 127 represent?",
            options: [
                { key: "A", text: "Minimum battery voltage" },
                { key: "B", text: "Timestamp" },
                { key: "C", text: "Row index corresponding to minimum battery" },
                { key: "D", text: "Number of rows" }
            ],
            answer: "C"
        },
        {
            id: "q5",
            category: "STATISTICAL OUTLIERS",
            question: "A dataset's mean is 50 and standard deviation is 2. One value is 80.\n\nAssuming the distribution is approximately normal, what is the first thing you'd suspect?",
            options: [
                { key: "A", text: "It is unusually far from the mean" },
                { key: "B", text: "It must be exactly correct" },
                { key: "C", text: "The mean must be wrong" },
                { key: "D", text: "Standard deviation cannot be used here" }
            ],
            answer: "A"
        },
        {
            id: "q6",
            category: "GRAPH INTERPRETATION",
            question: "A graph appears to show a strong relationship between two variables. You discover the graph's x-axis starts at 99 instead of 0.\n\nWhat can this change?",
            options: [
                { key: "A", text: "It can visually exaggerate the apparent change" },
                { key: "B", text: "It changes the actual correlation automatically" },
                { key: "C", text: "It changes the raw data" },
                { key: "D", text: "It removes outliers" }
            ],
            answer: "A"
        },
        {
            id: "q7",
            category: "COMMUNICATION DROPOUT",
            question: "A sensor stops updating for 30 seconds, then resumes with plausible values.\n\nWhich evidence would best distinguish a communication dropout from a physically constant value?",
            options: [
                { key: "A", text: "Check whether timestamps continue while the sensor value remains unchanged" },
                { key: "B", text: "Calculate only the overall mean" },
                { key: "C", text: "Sort the values alphabetically" },
                { key: "D", text: "Delete the 30-second interval" }
            ],
            answer: "A"
        }
    ],

    // =========================================================================
    // SLOT 5 — Finalist Position #5
    // =========================================================================
    slot5: [
        {
            id: "q1",
            category: "PANDAS ANALYSIS",
            question: "```python\ndf[\"altitude\"].diff().abs().nlargest(2)\n```\nWhat is this most useful for finding?",
            options: [
                { key: "A", text: "The two highest altitude readings" },
                { key: "B", text: "The two largest consecutive altitude changes" },
                { key: "C", text: "The two earliest timestamps" },
                { key: "D", text: "The two smallest altitude values" }
            ],
            answer: "B"
        },
        {
            id: "q2",
            category: "VARIABILITY ANALYSIS",
            question: "A sensor's average value is unchanged before and after an event, but its standard deviation doubles.\n\nWhat changed?",
            options: [
                { key: "A", text: "Typical level" },
                { key: "B", text: "Variability" },
                { key: "C", text: "Number of rows necessarily" },
                { key: "D", text: "Measurement units" }
            ],
            answer: "B"
        },
        {
            id: "q3",
            category: "SIGNAL PATTERN RECOGNITION",
            question: "A signal changes from:\n\n5, 5, 5, 5 → 8, 8, 8, 8\n\nWhich description fits best?",
            options: [
                { key: "A", text: "Isolated outlier" },
                { key: "B", text: "Sustained level shift" },
                { key: "C", text: "Random noise" },
                { key: "D", text: "Missing data" }
            ],
            answer: "B"
        },
        {
            id: "q4",
            category: "CORRELATION STABILITY",
            question: "A correlation of 0.85 is observed between two telemetry variables.\n\nWhich additional finding would most strongly challenge the idea that their relationship is stable?",
            options: [
                { key: "A", text: "Correlation is also 0.85 in another interval" },
                { key: "B", text: "Correlation becomes -0.10 during a different flight phase" },
                { key: "C", text: "Both variables have the same number of rows" },
                { key: "D", text: "Both variables are stored in CSV format" }
            ],
            answer: "B"
        },
        {
            id: "q5",
            category: "MISSINGNESS ANALYSIS",
            question: "A dataset has 5% missing values overall. But 40% of the readings during parachute deployment are missing.\n\nWhy is the overall 5% potentially misleading?",
            options: [
                { key: "A", text: "Overall averages can hide phase-specific missingness" },
                { key: "B", text: "Missing values never matter" },
                { key: "C", text: "Deployment data should always be ignored" },
                { key: "D", text: "5% is mathematically impossible" }
            ],
            answer: "A"
        },
        {
            id: "q6",
            category: "MULTI-SENSOR INTERPRETATION",
            question: "You see:\n\n• altitude ↓\n• pressure ↑\n• GPS altitude ↓\n• vertical velocity ↓\n\nBut acceleration shows a brief spike.\n\nWhat is the best interpretation?",
            options: [
                { key: "A", text: "The entire descent is invalid" },
                { key: "B", text: "The acceleration spike should be examined in the context of an otherwise consistent descent" },
                { key: "C", text: "All other sensors must be wrong" },
                { key: "D", text: "Acceleration can never change during descent" }
            ],
            answer: "B"
        },
        {
            id: "q7",
            category: "ANOMALY DETECTION",
            question: "You train an anomaly detector on mostly normal flight data. It flags almost every reading during parachute deployment.\n\nWhat is the most likely issue?",
            options: [
                { key: "A", text: "Deployment must be faulty" },
                { key: "B", text: "The model may not have learned that deployment is a legitimate different operating state" },
                { key: "C", text: "More anomalies always mean better detection" },
                { key: "D", text: "The dataset contains no useful information" }
            ],
            answer: "B"
        }
    ]
};
