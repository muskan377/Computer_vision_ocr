const fileInput = document.getElementById("file");
const preview = document.getElementById("preview");
const fileName = document.getElementById("fileName");
const analyzeBtn = document.getElementById("analyze");
const status = document.getElementById("status");
const progress = document.getElementById("progress");
const statusText = document.getElementById("statusText");
const statusPct = document.getElementById("statusPct");
const results = document.getElementById("results");
const drop = document.getElementById("drop");

let progressTimer = null;
let pipelineTimer = null;
let currentProgress = 0;


/* ---------------------------------------------------------
   FILE SELECTION
--------------------------------------------------------- */

fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];

    if (!file) {
        return;
    }

    fileName.textContent = file.name;
    statusText.textContent = `Ready: ${file.name}`;

    if (preview.src && preview.src.startsWith("blob:")) {
        URL.revokeObjectURL(preview.src);
    }

    preview.src = URL.createObjectURL(file);
    preview.classList.remove("hidden");
});


/* ---------------------------------------------------------
   PROGRESS
--------------------------------------------------------- */

function setProgress(percent, message) {
    currentProgress = Number(percent) || 0;

    progress.style.width = `${currentProgress}%`;
    statusPct.textContent =
        `${Math.round(currentProgress)}%`;

    statusText.textContent = message;
}


/* ---------------------------------------------------------
   CONTINUOUS PROGRESS
--------------------------------------------------------- */

function startContinuousProgress() {

    clearInterval(progressTimer);

    const messages = [
        "Scanning video frames…",
        "Locating scoreboard…",
        "Cropping scoreboard region…",
        "Preprocessing scoreboard…",
        "Running EasyOCR…",
        "Reading score cells…",
        "Validating OCR results…",
        "Comparing multiple frames…",
        "Fusing scoreboard observations…"
    ];

    let messageIndex = 0;
    let messageCounter = 0;

    currentProgress = 15;

    setProgress(
        currentProgress,
        messages[0]
    );

    progressTimer = setInterval(() => {

        /*
         * Move smoothly from 15% to 92%.
         * Never reaches 100 until backend is actually done.
         */
        if (currentProgress < 91.5) {

            currentProgress += 0.22;

            progress.style.width =
                `${currentProgress}%`;

            statusPct.textContent =
                `${Math.floor(currentProgress)}%`;
        }

        /*
         * Change pipeline stage message
         * every few seconds.
         */
        messageCounter++;

        if (messageCounter >= 18) {

            messageCounter = 0;

            messageIndex =
                (messageIndex + 1) %
                messages.length;

            statusText.textContent =
                messages[messageIndex];
        }

    }, 120);
}


/* ---------------------------------------------------------
   STOP PROGRESS
--------------------------------------------------------- */

function stopContinuousProgress(
    percent,
    message
) {
    clearInterval(progressTimer);
    progressTimer = null;

    setProgress(
        percent,
        message
    );
}


/* ---------------------------------------------------------
   PIPELINE ANIMATION
--------------------------------------------------------- */

function startPipelineAnimation() {

    const steps =
        document.querySelectorAll(".pipeline .step");

    const arrows =
        document.querySelectorAll(".pipeline .arrow");

    if (!steps.length) {
        return;
    }

    let index = 0;

    steps.forEach(step => {
        step.classList.remove(
            "active",
            "complete"
        );
    });

    arrows.forEach(arrow => {
        arrow.classList.remove(
            "active",
            "complete"
        );
    });

    clearInterval(pipelineTimer);

    /*
     * Highlight pipeline stages one by one.
     */
    pipelineTimer = setInterval(() => {

        steps.forEach((step, i) => {

            step.classList.remove(
                "active",
                "complete"
            );

            if (i < index) {
                step.classList.add(
                    "complete"
                );
            }

            if (i === index) {
                step.classList.add(
                    "active"
                );
            }
        });

        arrows.forEach((arrow, i) => {

            arrow.classList.remove(
                "active",
                "complete"
            );

            if (i < index) {
                arrow.classList.add(
                    "complete"
                );
            }

            if (i === index) {
                arrow.classList.add(
                    "active"
                );
            }
        });

        index++;

        if (index >= steps.length) {
            index = 0;
        }

    }, 2200);
}


/* ---------------------------------------------------------
   COMPLETE PIPELINE ANIMATION
--------------------------------------------------------- */

function finishPipelineAnimation() {

    clearInterval(pipelineTimer);
    pipelineTimer = null;

    const steps =
        document.querySelectorAll(".pipeline .step");

    const arrows =
        document.querySelectorAll(".pipeline .arrow");

    steps.forEach(step => {

        step.classList.remove("active");

        step.classList.add(
            "complete"
        );
    });

    arrows.forEach(arrow => {

        arrow.classList.remove("active");

        arrow.classList.add(
            "complete"
        );
    });
}


/* ---------------------------------------------------------
   HTML SAFETY
--------------------------------------------------------- */

function escapeHtml(value) {

    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


/* ---------------------------------------------------------
   CONFIDENCE
--------------------------------------------------------- */

function confidenceClass(confidence) {

    const value =
        Number(confidence) || 0;

    if (value >= 0.80) {
        return "high";
    }

    if (value >= 0.60) {
        return "medium";
    }

    return "low";
}


/* ---------------------------------------------------------
   CELL DISPLAY
--------------------------------------------------------- */

function renderCells(cells) {

    if (
        !Array.isArray(cells) ||
        cells.length === 0
    ) {
        return "—";
    }

    return cells
        .map(cell => {

            const value =
                cell?.value ||
                cell?.raw_text ||
                "";

            return value
                ? escapeHtml(value)
                : "—";
        })
        .join(" • ");
}


/* ---------------------------------------------------------
   RESULT RENDER
--------------------------------------------------------- */

function render(data) {

    if (
        !data ||
        typeof data !== "object"
    ) {
        throw new Error(
            "The server returned an invalid result."
        );
    }

    const players =
        data.players &&
        typeof data.players === "object"
            ? data.players
            : {};

    let html = `
        <table class="table">
            <thead>
                <tr>
                    <th>Row</th>
                    <th>OCR Text</th>
                    <th>Numbers</th>
                    <th>Confidence</th>
                    <th>Frames</th>
                </tr>
            </thead>
            <tbody>
    `;

    const entries =
        Object.entries(players);

    if (entries.length === 0) {

        html += `
            <tr>
                <td colspan="5">
                    No scoreboard rows were extracted.
                </td>
            </tr>
        `;

    } else {

        for (
            const [player, row]
            of entries
        ) {

            const confidence =
                Number(
                    row?.confidence
                ) || 0;

            const confidencePercent =
                Math.round(
                    confidence * 100
                );

            const numbers =
                Array.isArray(
                    row?.numbers_detected
                )
                    ? row.numbers_detected
                        .map(value =>
                            escapeHtml(value)
                        )
                        .join(" • ")
                    : (
                        row?.numbers_detected ||
                        "—"
                    );

            const cells =
                Array.isArray(row?.cells)
                    ? row.cells
                    : [];

            const displayText =
                row?.raw_text ||
                (
                    cells.length
                        ? renderCells(cells)
                        : "—"
                );

            html += `
                <tr>
                    <td>
                        <b>
                            ${escapeHtml(player)}
                        </b>
                    </td>

                    <td>
                        ${escapeHtml(displayText)}
                    </td>

                    <td>
                        ${numbers || "—"}
                    </td>

                    <td>
                        <span
                            class="confidence ${confidenceClass(confidence)}"
                        >
                            ${confidencePercent}%
                        </span>
                    </td>

                    <td>
                        ${Number(
                            row?.observations
                        ) || 0}
                    </td>
                </tr>
            `;
        }
    }

    html += `
            </tbody>
        </table>
    `;

    const scoreTable =
        document.getElementById(
            "scoreTable"
        );

    if (scoreTable) {
        scoreTable.innerHTML = html;
    }


    /* -----------------------------------------------------
       META
    ----------------------------------------------------- */

    const duration =
        data.video_info?.duration_seconds ?? 0;

    const detected =
        data.scoreboard_frames_detected ?? 0;

    const ocrFrames =
        data.ocr_frames_used ?? 0;

    const meta =
        document.getElementById("meta");

    if (meta) {

        meta.textContent =
            `${duration}s • ` +
            `${detected} detected • ` +
            `${ocrFrames} OCR frames`;
    }


    /* -----------------------------------------------------
       CURRENT PLAYER
    ----------------------------------------------------- */

    const currentPlayer =
        document.getElementById(
            "currentPlayer"
        );

    if (currentPlayer) {

        const name =
            data.current_name ||
            "—";

        const confidence =
            Math.round(
                (
                    Number(
                        data.current_name_confidence
                    ) || 0
                ) * 100
            );

        currentPlayer.textContent =
            `${name} (${confidence}%)`;
    }


    results.classList.remove(
        "hidden"
    );
}


/* ---------------------------------------------------------
   ANALYZE
--------------------------------------------------------- */

async function analyze() {

    const file =
        fileInput.files[0];

    if (!file) {

        alert(
            "Please select bowling_scoreboard.mp4 first."
        );

        return;
    }

    status.classList.remove(
        "hidden"
    );

    results.classList.add(
        "hidden"
    );

    analyzeBtn.disabled = true;

    setProgress(
        5,
        "Preparing video…"
    );

    const formData =
        new FormData();

    formData.append(
        "video",
        file
    );

    try {

        /* -------------------------------------------------
           START PIPELINE VISUALS
        ------------------------------------------------- */

        startPipelineAnimation();


        /* -------------------------------------------------
           UPLOAD
        ------------------------------------------------- */

        setProgress(
            12,
            "Uploading video…"
        );

        /*
         * Start continuous progress BEFORE fetch.
         * This is important because fetch waits for
         * the backend analysis to finish.
         */

        startContinuousProgress();


        /* -------------------------------------------------
           API CALL
        ------------------------------------------------- */

        const response =
            await fetch(
                "/api/analyze",
                {
                    method: "POST",
                    body: formData
                }
            );


        /* -------------------------------------------------
           READ RESPONSE
        ------------------------------------------------- */

        let data;

        try {

            data =
                await response.json();

        } catch (jsonError) {

            throw new Error(
                `Server returned invalid response (${response.status}).`
            );
        }


        /* -------------------------------------------------
           BACKEND ERROR
        ------------------------------------------------- */

        if (!response.ok) {

            throw new Error(
                data?.error ||
                `Analysis failed (${response.status}).`
            );
        }


        if (!data.job_id) {

            throw new Error(
                "Analysis completed but no job ID was returned."
            );
        }


        /* -------------------------------------------------
           FINISH PROGRESS
        ------------------------------------------------- */

        stopContinuousProgress(
            94,
            "Preparing final scoreboard…"
        );


        /* -------------------------------------------------
           RESULT FILES
        ------------------------------------------------- */

        const baseUrl =
            `/api/jobs/${encodeURIComponent(
                data.job_id
            )}/`;


        const best =
            document.getElementById(
                "best"
            );

        if (best) {

            best.src =
                baseUrl +
                "annotated/best_frame.jpg";
        }


        const json =
            document.getElementById(
                "json"
            );

        if (json) {

            json.href =
                baseUrl +
                "scoreboard_data.json";
        }


        const csv =
            document.getElementById(
                "csv"
            );

        if (csv) {

            csv.href =
                baseUrl +
                "scoreboard_data.csv";
        }


        /* -------------------------------------------------
           RENDER
        ------------------------------------------------- */

        setProgress(
            97,
            "Building final scoreboard…"
        );

        render(data);


        /* -------------------------------------------------
           COMPLETE
        ------------------------------------------------- */

        finishPipelineAnimation();

        setProgress(
            100,
            "Extraction complete"
        );

        results.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });


    } catch (error) {

        console.error(
            "ScoreVision analysis error:",
            error
        );

        clearInterval(
            progressTimer
        );

        progressTimer = null;

        clearInterval(
            pipelineTimer
        );

        pipelineTimer = null;

        setProgress(
            100,
            "Analysis failed"
        );

        alert(
            error?.message ||
            "Something went wrong while analyzing the video."
        );


    } finally {

        analyzeBtn.disabled = false;
    }
}


/* ---------------------------------------------------------
   BUTTON
--------------------------------------------------------- */

analyzeBtn.addEventListener(
    "click",
    event => {

        event.preventDefault();
        event.stopPropagation();

        analyze();
    }
);


/* ---------------------------------------------------------
   DROP AREA
--------------------------------------------------------- */

drop.addEventListener(
    "click",
    event => {

        if (
            event.target.id !== "analyze" &&
            !analyzeBtn.contains(
                event.target
            )
        ) {

            fileInput.click();
        }
    }
);


/* ---------------------------------------------------------
   DRAG & DROP
--------------------------------------------------------- */

drop.addEventListener(
    "dragover",
    event => {

        event.preventDefault();

        drop.classList.add(
            "dragover"
        );
    }
);


drop.addEventListener(
    "dragleave",
    () => {

        drop.classList.remove(
            "dragover"
        );
    }
);


drop.addEventListener(
    "drop",
    event => {

        event.preventDefault();

        drop.classList.remove(
            "dragover"
        );

        const file =
            event.dataTransfer.files[0];

        if (!file) {
            return;
        }

        try {

            const dataTransfer =
                new DataTransfer();

            dataTransfer.items.add(file);

            fileInput.files =
                dataTransfer.files;

            fileInput.dispatchEvent(
                new Event("change")
            );

        } catch (error) {

            console.error(
                "Drag/drop error:",
                error
            );
        }
    }
);