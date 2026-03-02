(function () {
    var state = {
        currentStep: 1,
        jobId: null,
        jdMode: "upload",
        jdFile: null,
        resumes: [],
        results: [],
        isUploading: false,
        isAnalyzing: false,
        analysisResult: null,
        viewingJobId: null,
        selectedIds: new Set(),
        activeSkill: null
    };

    var els = {};

    function refreshIcons() {
        setTimeout(function () { feather.replace(); }, 0);
    }

    function init() {
        cacheElements();
        bindStep1();
        bindStep2();
        bindStep3();
        bindStep4();
        bindFilters();
        bindModals();
        restoreDraft();
        refreshIcons();
        if (window.setupDashboardReveal) window.setupDashboardReveal();
    }

    function cacheElements() {
        els.steps = document.querySelectorAll(".wizard-step");
        els.connectors = document.querySelectorAll(".wizard-step-connector");
        els.panels = document.querySelectorAll(".wizard-panel");
        els.wizardContainer = document.getElementById("wizard-container");
        els.jdToggleBtns = document.querySelectorAll(".jd-toggle-btn");
        els.jdUploadArea = document.getElementById("jd-upload-area");
        els.jdPasteArea = document.getElementById("jd-paste-area");
        els.jdDropZone = document.getElementById("jd-drop-zone");
        els.jdFileInput = document.getElementById("jd-file-input");
        els.jdBrowseBtn = document.getElementById("jd-browse-btn");
        els.jdFilePreview = document.getElementById("jd-file-preview");
        els.jdFileName = document.getElementById("jd-file-name");
        els.jdFileRemove = document.getElementById("jd-file-remove");
        els.jdTextarea = document.getElementById("jd-textarea");
        els.jdNextBtn = document.getElementById("jd-next-btn");
        els.jdWizardNav = document.getElementById("jd-wizard-nav");
        els.jdAnalyzing = document.getElementById("jd-analyzing");
        els.jdAnalysisResult = document.getElementById("jd-analysis-result");
        els.analysisFields = document.getElementById("analysis-fields");
        els.analysisSkillsWrap = document.getElementById("analysis-skills-wrap");
        els.analysisSkillsList = document.getElementById("analysis-skills-list");
        els.analysisContinueBtn = document.getElementById("analysis-continue-btn");
        els.resumeDropZone = document.getElementById("resume-drop-zone");
        els.resumeFileInput = document.getElementById("resume-file-input");
        els.resumeBrowseBtn = document.getElementById("resume-browse-btn");
        els.resumeList = document.getElementById("resume-list");
        els.resumeItems = document.getElementById("resume-items");
        els.resumeCount = document.getElementById("resume-count");
        els.addMoreBtn = document.getElementById("add-more-btn");
        els.resumeBackBtn = document.getElementById("resume-back-btn");
        els.startScreeningBtn = document.getElementById("start-screening-btn");
        els.screeningLoading = document.getElementById("screening-loading");
        els.screeningResults = document.getElementById("screening-results");
        els.resultsGrid = document.getElementById("results-grid");
        els.progressFill = document.getElementById("screening-progress-fill");
        els.progressPercent = document.getElementById("screening-progress-percent");
        els.screeningResumeCount = document.getElementById("screening-resume-count");
        els.resultsBackBtn = document.getElementById("results-back-btn");
        els.sortSelect = document.getElementById("sort-select");
        els.skillFilter = document.getElementById("skill-filter");
        els.skillFilterPills = document.getElementById("skill-filter-pills");
        els.selectionBar = document.getElementById("selection-bar");
        els.selectionCount = document.getElementById("selection-count");
        els.selectAllCheckbox = document.getElementById("select-all-checkbox");
        els.exportPdfBtn = document.getElementById("export-pdf-btn");
        els.sendInviteBtn = document.getElementById("send-invite-btn");
        els.inviteModal = document.getElementById("invite-modal");
        els.inviteModalClose = document.getElementById("invite-modal-close");
        els.inviteSchedulingLink = document.getElementById("invite-scheduling-link");
        els.inviteMessage = document.getElementById("invite-message");
        els.inviteCancelBtn = document.getElementById("invite-cancel-btn");
        els.inviteSubmitBtn = document.getElementById("invite-submit-btn");
        els.resumePreviewModal = document.getElementById("resume-preview-modal");
        els.resumePreviewClose = document.getElementById("resume-preview-close");
        els.resumePreviewName = document.getElementById("resume-preview-name");
        els.resumePreviewIframe = document.getElementById("resume-preview-iframe");
        els.step4StatusGroups = document.getElementById("step4-status-groups");
        els.step4BackBtn = document.getElementById("step4-back-btn");
        els.finalDecisionModal = document.getElementById("final-decision-modal");
        els.finalDecisionClose = document.getElementById("final-decision-close");
        els.finalDecisionTitle = document.getElementById("final-decision-title");
        els.finalDecisionId = document.getElementById("final-decision-id");
        els.finalDecisionType = document.getElementById("final-decision-type");
        els.finalDecisionNotes = document.getElementById("final-decision-notes");
        els.finalDecisionCancel = document.getElementById("final-decision-cancel");
        els.finalDecisionSubmit = document.getElementById("final-decision-submit");
    }

    function resetWizardState() {
        state.jobId = null;
        state.resumes = [];
        state.results = [];
        state.viewingJobId = null;
        state.jdFile = null;
        state.analysisResult = null;
        state.isAnalyzing = false;
        state.selectedIds.clear();
        els.jdFilePreview.style.display = "none";
        els.jdDropZone.style.display = "";
        els.jdTextarea.value = "";
        els.jdFileInput.value = "";
        els.jdAnalyzing.style.display = "none";
        els.jdAnalysisResult.style.display = "none";
        els.jdWizardNav.style.display = "";
        updateNextBtn();
    }

    function showWizard() {
        els.wizardContainer.style.display = "";
    }

    function goToStep(step) {
        state.currentStep = step;

        els.steps.forEach(function (el, i) {
            var stepNum = i + 1;
            el.classList.remove("active", "completed");
            if (stepNum === step) el.classList.add("active");
            else if (stepNum < step) el.classList.add("completed");
        });

        els.connectors.forEach(function (el, i) {
            el.classList.toggle("completed", i < step - 1);
        });

        els.panels.forEach(function (panel) { panel.classList.remove("active"); });
        var target = document.getElementById("step-" + step + "-panel");
        if (target) target.classList.add("active");

        if (step === 4) loadStep4Candidates();

        refreshIcons();
    }

    function bindStep1() {
        els.jdToggleBtns.forEach(function (btn) {
            btn.addEventListener("click", function () {
                els.jdToggleBtns.forEach(function (b) { b.classList.remove("active"); });
                btn.classList.add("active");
                state.jdMode = btn.dataset.mode;
                els.jdUploadArea.style.display = state.jdMode === "upload" ? "" : "none";
                els.jdPasteArea.style.display = state.jdMode === "paste" ? "" : "none";
                updateNextBtn();
                refreshIcons();
            });
        });

        setupDropZone(els.jdDropZone, els.jdFileInput, handleJdFiles);
        els.jdBrowseBtn.addEventListener("click", function () { els.jdFileInput.click(); });
        els.jdFileInput.addEventListener("change", function () { handleJdFiles(els.jdFileInput.files); });

        els.jdFileRemove.addEventListener("click", function () {
            state.jdFile = null;
            els.jdFilePreview.style.display = "none";
            els.jdDropZone.style.display = "";
            updateNextBtn();
            refreshIcons();
        });

        els.jdTextarea.addEventListener("input", updateNextBtn);
        els.jdNextBtn.addEventListener("click", submitJd);
    }

    function handleJdFiles(files) {
        if (!files || !files.length) return;
        var file = files[0];
        if (!file.name.toLowerCase().endsWith(".pdf")) {
            window.toast("Only PDF files are supported", "error");
            return;
        }
        state.jdFile = file;
        els.jdFileName.textContent = file.name;
        els.jdDropZone.style.display = "none";
        els.jdFilePreview.style.display = "";
        updateNextBtn();
        refreshIcons();
    }

    function updateNextBtn() {
        var hasInput = false;
        if (state.jdMode === "upload") {
            hasInput = state.jdFile !== null;
        } else {
            hasInput = els.jdTextarea.value.trim().length > 0;
        }
        els.jdNextBtn.disabled = !hasInput;
    }

    function submitJd() {
        if (state.isUploading) return;
        state.isUploading = true;
        els.jdNextBtn.disabled = true;
        els.jdNextBtn.textContent = "Uploading...";

        var formData = new FormData();
        if (state.jdMode === "upload" && state.jdFile) {
            formData.append("jd_file", state.jdFile);
        } else {
            formData.append("jd_text", els.jdTextarea.value.trim());
        }

        fetch("/dashboard/upload-jd", { method: "POST", body: formData })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                state.isUploading = false;
                if (data.success) {
                    state.jobId = data.job_id;
                    window.toast("Job description saved", "success");
                    analyzeJd(data.job_id);
                } else {
                    window.toast(data.error || "Upload failed", "error");
                }
            })
            .catch(function () {
                state.isUploading = false;
                window.toast("Network error. Please try again.", "error");
            })
            .finally(function () {
                els.jdNextBtn.textContent = "";
                els.jdNextBtn.innerHTML = 'Next <i data-feather="arrow-right"></i>';
                updateNextBtn();
                refreshIcons();
            });
    }

    function analyzeJd(jobId) {
        state.isAnalyzing = true;
        els.jdUploadArea.style.display = "none";
        els.jdPasteArea.style.display = "none";
        els.jdFilePreview.style.display = "none";
        els.jdWizardNav.style.display = "none";
        els.jdAnalyzing.style.display = "";
        els.jdAnalysisResult.style.display = "none";
        var toggle = document.querySelector(".jd-input-toggle");
        if (toggle) toggle.style.display = "none";

        fetch("/dashboard/analyze-jd/" + jobId, { method: "POST" })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                state.isAnalyzing = false;
                if (data.success) {
                    state.analysisResult = data.analysis;
                    showAnalysisResult(data.analysis);
                } else {
                    if (data.fallback) {
                        window.toast("AI analysis unavailable, proceeding to resume upload", "error");
                    } else {
                        window.toast(data.error || "Analysis failed", "error");
                    }
                    els.jdAnalyzing.style.display = "none";
                    resetStep1Ui();
                    goToStep(2);
                }
            })
            .catch(function () {
                state.isAnalyzing = false;
                window.toast("Network error during analysis, proceeding to resume upload", "error");
                els.jdAnalyzing.style.display = "none";
                resetStep1Ui();
                goToStep(2);
            });
    }

    function showAnalysisResult(analysis) {
        els.jdAnalyzing.style.display = "none";
        els.jdAnalysisResult.style.display = "";

        var fields = [
            { label: "Job Title", value: analysis.title },
            { label: "Department", value: analysis.department },
            { label: "Location", value: analysis.location },
            { label: "Seniority", value: analysis.seniority_level },
            { label: "Type", value: analysis.employment_type },
            { label: "Salary", value: analysis.salary_range }
        ];

        els.analysisFields.innerHTML = "";
        fields.forEach(function (f) {
            if (!f.value) return;
            var div = document.createElement("div");
            div.className = "analysis-field";
            div.innerHTML = '<span class="analysis-field-label">' + escapeHtml(f.label) + '</span>' +
                '<span class="analysis-field-value">' + escapeHtml(f.value) + '</span>';
            els.analysisFields.appendChild(div);
        });

        if (analysis.key_skills && analysis.key_skills.length) {
            els.analysisSkillsWrap.style.display = "";
            els.analysisSkillsList.innerHTML = "";
            analysis.key_skills.forEach(function (skill) {
                var span = document.createElement("span");
                span.className = "pill-tag";
                span.textContent = skill;
                els.analysisSkillsList.appendChild(span);
            });
        } else {
            els.analysisSkillsWrap.style.display = "none";
        }

        els.analysisContinueBtn.addEventListener("click", function handler() {
            els.analysisContinueBtn.removeEventListener("click", handler);
            resetStep1Ui();
            goToStep(2);
        });

        refreshIcons();

        setTimeout(function () {
            if (els.jdAnalysisResult.style.display !== "none" && state.currentStep === 1) {
                resetStep1Ui();
                goToStep(2);
            }
        }, 4000);
    }

    function resetStep1Ui() {
        els.jdAnalyzing.style.display = "none";
        els.jdAnalysisResult.style.display = "none";
        els.jdWizardNav.style.display = "";
        var toggle = document.querySelector(".jd-input-toggle");
        if (toggle) toggle.style.display = "";
        if (state.jdMode === "upload") {
            els.jdUploadArea.style.display = "";
        } else {
            els.jdPasteArea.style.display = "";
        }
        state.analysisResult = null;
    }

    function bindStep2() {
        setupDropZone(els.resumeDropZone, els.resumeFileInput, handleResumeFiles);
        els.resumeBrowseBtn.addEventListener("click", function () { els.resumeFileInput.click(); });
        els.resumeFileInput.addEventListener("change", function () { handleResumeFiles(els.resumeFileInput.files); });

        els.addMoreBtn.addEventListener("click", function () { els.resumeFileInput.click(); });
        els.resumeBackBtn.addEventListener("click", function () { goToStep(1); });
        els.startScreeningBtn.addEventListener("click", startScreening);
    }

    function handleResumeFiles(files) {
        if (!files || !files.length || !state.jobId) return;

        var pdfs = Array.from(files).filter(function (f) { return f.name.toLowerCase().endsWith(".pdf"); });
        if (pdfs.length === 0) {
            window.toast("Only PDF files are supported", "error");
            return;
        }

        els.resumeDropZone.classList.add("uploading");
        var uploaded = 0;
        var failed = 0;
        var total = pdfs.length;

        function uploadNext(i) {
            if (i >= total) {
                els.resumeDropZone.classList.remove("uploading");
                if (uploaded > 0) {
                    renderResumeList();
                    window.toast(uploaded + "/" + total + " resume(s) uploaded", "success");
                } else {
                    window.toast("No valid resumes could be processed", "error");
                }
                return;
            }

            window.toast("Uploading " + (i + 1) + "/" + total + ": " + pdfs[i].name, "info");
            var formData = new FormData();
            formData.append("resumes", pdfs[i]);

            fetch("/dashboard/upload-resumes/" + state.jobId, { method: "POST", body: formData })
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    if (data.success && data.candidates && data.candidates.length) {
                        data.candidates.forEach(function (c) { state.resumes.push(c); });
                        uploaded++;
                        renderResumeList();
                    } else {
                        failed++;
                    }
                    uploadNext(i + 1);
                })
                .catch(function () {
                    failed++;
                    uploadNext(i + 1);
                });
        }

        uploadNext(0);
        els.resumeFileInput.value = "";
    }

    function renderResumeList() {
        if (state.resumes.length === 0) {
            els.resumeList.style.display = "none";
            els.resumeDropZone.style.display = "";
            els.startScreeningBtn.disabled = true;
            return;
        }

        els.resumeList.style.display = "";
        els.resumeDropZone.style.display = "none";
        els.resumeCount.textContent = state.resumes.length + " resume" + (state.resumes.length === 1 ? "" : "s") + " uploaded";
        els.startScreeningBtn.disabled = false;

        els.resumeItems.innerHTML = "";
        state.resumes.forEach(function (r) {
            var item = document.createElement("div");
            item.className = "resume-item";
            item.dataset.id = r.id;
            item.innerHTML =
                '<i data-feather="file-text"></i>' +
                '<span class="resume-item-name">' + escapeHtml(r.filename) + '</span>' +
                '<button class="resume-item-remove" type="button" aria-label="Remove resume"><i data-feather="x"></i></button>';
            item.querySelector(".resume-item-remove").addEventListener("click", function () { removeResume(r.id); });
            els.resumeItems.appendChild(item);
        });

        refreshIcons();
    }

    function removeResume(candidateId) {
        fetch("/dashboard/remove-resume/" + candidateId, { method: "DELETE" })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.success) {
                    state.resumes = state.resumes.filter(function (r) { return r.id !== candidateId; });
                    renderResumeList();
                }
            })
            .catch(function () { window.toast("Could not remove resume", "error"); });
    }

    function setupDropZone(zone, input, handler) {
        ["dragenter", "dragover"].forEach(function (evt) {
            zone.addEventListener(evt, function (e) {
                e.preventDefault();
                zone.classList.add("drop-zone-active");
            });
        });

        ["dragleave", "drop"].forEach(function (evt) {
            zone.addEventListener(evt, function (e) {
                e.preventDefault();
                zone.classList.remove("drop-zone-active");
            });
        });

        zone.addEventListener("drop", function (e) {
            handler(e.dataTransfer.files);
        });
    }

    function bindStep3() {
        els.resultsBackBtn.addEventListener("click", function () {
            resetWizardState();
            goToStep(1);
        });

        els.selectAllCheckbox.addEventListener("change", function () {
            var checked = els.selectAllCheckbox.checked;
            var visible = getFilteredResults();
            if (checked) {
                visible.forEach(function (r) { state.selectedIds.add(r.id); });
            } else {
                state.selectedIds.clear();
            }
            syncResultCheckboxes();
            updateSelectionBar();
        });

        els.resultsGrid.addEventListener("click", function (e) {
            var checkbox = e.target.closest(".result-card-checkbox");
            if (checkbox) {
                var id = parseInt(checkbox.dataset.id);
                if (checkbox.checked) {
                    state.selectedIds.add(id);
                } else {
                    state.selectedIds.delete(id);
                }
                syncSelectAllCheckbox();
                updateSelectionBar();
                var card = checkbox.closest(".result-card");
                if (card) card.classList.toggle("result-card--selected", checkbox.checked);
                return;
            }

            var pdfBtn = e.target.closest(".card-pdf-btn");
            if (pdfBtn) {
                openReportPreview(pdfBtn.dataset.id, pdfBtn.dataset.name);
                return;
            }

            var nameTrigger = e.target.closest(".resume-preview-trigger");
            if (nameTrigger) {
                openResumePreview(nameTrigger.dataset.id, nameTrigger.dataset.name);
                return;
            }

        });

        els.resultsGrid.addEventListener("keydown", function (e) {
            var nameTrigger = e.target.closest(".resume-preview-trigger");
            if (!nameTrigger) return;
            if (e.key === "Enter" || e.key === " " || e.key === "Spacebar") {
                e.preventDefault();
                openResumePreview(nameTrigger.dataset.id, nameTrigger.dataset.name);
            }
        });

        els.exportPdfBtn.addEventListener("click", exportSelectedPdfs);
        els.sendInviteBtn.addEventListener("click", openInviteModal);
    }

    function bindFilters() {
        els.sortSelect.addEventListener("change", applyFilters);

        els.skillFilterPills.addEventListener("click", function (e) {
            var pill = e.target.closest(".skill-filter-pill");
            if (!pill) return;
            var skill = pill.dataset.skill;
            if (state.activeSkill === skill) {
                state.activeSkill = null;
                pill.classList.remove("active");
            } else {
                els.skillFilterPills.querySelectorAll(".skill-filter-pill").forEach(function (p) { p.classList.remove("active"); });
                pill.classList.add("active");
                state.activeSkill = skill;
            }
            applyFilters();
        });
    }

    function getFilteredResults() {
        var sortKey = els.sortSelect.value;

        var filtered = state.results.slice();

        if (state.activeSkill) {
            var skill = state.activeSkill;
            filtered = filtered.filter(function (r) {
                return r.matched_skills && r.matched_skills.some(function (s) {
                    return s.toLowerCase() === skill.toLowerCase();
                });
            });
        }

        filtered.sort(function (a, b) {
            return (b[sortKey] || 0) - (a[sortKey] || 0);
        });

        return filtered;
    }

    function applyFilters() {
        if (!state.results.length) return;
        var filtered = getFilteredResults();
        renderResultCards(filtered);
        syncSelectAllCheckbox();
        updateSelectionBar();
    }

    function startScreening() {
        if (!state.jobId) return;

        var totalResumes = state.resumes.length;

        goToStep(3);
        els.screeningLoading.style.display = "";
        els.screeningResults.style.display = "none";
        state.selectedIds.clear();

        var progress = 0;
        var fakeIndex = 0;
        els.progressFill.style.width = "0%";
        els.progressPercent.textContent = "0%";
        if (totalResumes > 0) {
            els.screeningResumeCount.textContent = "Analyzing resume 1 of " + totalResumes + "...";
        } else {
            els.screeningResumeCount.textContent = "";
        }

        var progressTimer = setInterval(function () {
            if (progress >= 90) return;
            progress += Math.floor(Math.random() * 8) + 2;
            if (progress > 90) progress = 90;
            els.progressFill.style.width = progress + "%";
            els.progressPercent.textContent = progress + "%";
            if (totalResumes > 1) {
                var estimated = Math.min(Math.floor((progress / 90) * totalResumes) + 1, totalResumes);
                if (estimated !== fakeIndex) {
                    fakeIndex = estimated;
                    els.screeningResumeCount.textContent = "Analyzing resume " + estimated + " of " + totalResumes + "...";
                }
            }
        }, 500);

        fetch("/dashboard/start-screening/" + state.jobId, { method: "POST" })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                clearInterval(progressTimer);
                els.progressFill.style.width = "100%";
                els.progressPercent.textContent = "100%";

                if (data.success) {
                    if (data.rate_limited) {
                        window.toast("Some resumes could not be analyzed due to AI rate limits. You can retry later.", "error");
                    }
                    setTimeout(function () {
                        state.results = data.results;
                        showScreeningResults(data.results);
                    }, 400);
                } else {
                    window.toast(data.error || "Screening failed", "error");
                    goToStep(2);
                    renderResumeList();
                }
            })
            .catch(function () {
                clearInterval(progressTimer);
                window.toast("Network error during screening", "error");
                goToStep(2);
                renderResumeList();
            });
    }

    function showScreeningResults(results) {
        els.screeningLoading.style.display = "none";
        els.screeningResults.style.display = "";
        state.results = results;
        state.selectedIds.clear();
        state.activeSkill = null;
        els.sortSelect.value = "match_score";

        var allSkills = {};
        results.forEach(function (r) {
            if (r.matched_skills) {
                r.matched_skills.forEach(function (s) {
                    var key = s.toLowerCase();
                    if (!allSkills[key]) allSkills[key] = { name: s, count: 0 };
                    allSkills[key].count++;
                });
            }
        });

        var skillEntries = Object.values(allSkills).sort(function (a, b) { return b.count - a.count; });
        els.skillFilterPills.innerHTML = "";
        if (skillEntries.length) {
            els.skillFilter.style.display = "";
            skillEntries.forEach(function (entry) {
                var pill = document.createElement("button");
                pill.className = "skill-filter-pill";
                pill.type = "button";
                pill.dataset.skill = entry.name;
                pill.textContent = entry.name + " (" + entry.count + ")";
                els.skillFilterPills.appendChild(pill);
            });
        } else {
            els.skillFilter.style.display = "none";
        }

        renderResultCards(results);
        updateSelectionBar();
    }

    function renderResultCards(results) {
        els.resultsGrid.innerHTML = "";

        if (results.length === 0) {
            els.resultsGrid.innerHTML = '<p class="results-empty">No candidates match the current filters.</p>';
            return;
        }

        results.forEach(function (r) {
            var scoreClass = r.match_score >= 90 ? "green" : r.match_score >= 70 ? "amber" : "red";
            var isSelected = state.selectedIds.has(r.id);
            var skillsHtml = "";
            if (r.matched_skills && r.matched_skills.length) {
                skillsHtml = '<div class="result-skills">' +
                    r.matched_skills.map(function (s) {
                        return '<span class="pill-tag">' + escapeHtml(s) + '</span>';
                    }).join("") +
                    '</div>';
            }

            var statusBadge = "";
            if (r.status === "invited") {
                statusBadge = '<span class="job-card-badge badge-invited">Invited</span>';
            } else if (r.status === "shortlisted") {
                statusBadge = '<span class="job-card-badge badge-shortlisted">Shortlisted</span>';
            } else if (r.status === "interview_done") {
                statusBadge = '<span class="job-card-badge badge-interview-done">Interview Done</span>';
            } else if (r.status === "final_hired") {
                statusBadge = '<span class="job-card-badge badge-final-hired">Hired</span>';
            } else if (r.status === "final_rejected") {
                statusBadge = '<span class="job-card-badge badge-final-rejected">Rejected</span>';
            }

            var tier = r.match_score >= 90 ? "excellent" : r.match_score >= 70 ? "good" : "low";
            var card = document.createElement("div");
            card.className = "result-card result-card--selectable" + (isSelected ? " result-card--selected" : "");
            card.dataset.tier = tier;
            card.innerHTML =
                '<div class="result-card-header">' +
                '<div class="result-card-info">' +
                '<label class="result-card-select">' +
                '<input type="checkbox" class="result-card-checkbox" data-id="' + r.id + '"' + (isSelected ? " checked" : "") + '>' +
                '</label>' +
                '<i data-feather="user"></i>' +
                '<div class="result-card-text">' +
                '<span class="result-card-name resume-preview-trigger" data-id="' + r.id + '" data-name="' + escapeHtml(r.candidate_name || r.filename) + '" tabindex="0" role="button">' + escapeHtml(r.candidate_name || r.filename) + '</span>' +
                '<span class="result-card-filename">' + escapeHtml(r.candidate_email || r.filename) + '</span>' +
                '</div>' +
                '</div>' +
                '<div style="display:flex;align-items:center;gap:8px;">' +
                statusBadge +
                '<div class="result-score ' + scoreClass + '">' + r.match_score + '</div>' +
                '</div>' +
                '</div>' +
                '<div class="result-breakdown">' +
                buildScoreBar("Skills", r.skills_score) +
                buildScoreBar("Experience", r.experience_score) +
                buildScoreBar("Education", r.education_score) +
                '</div>' +
                skillsHtml +
                '<p class="result-card-summary">' + escapeHtml(r.match_summary || "") + '</p>' +
                '<div class="result-card-actions">' +
                '<button class="card-pdf-btn" data-id="' + r.id + '" data-name="' + escapeHtml(r.candidate_name || r.filename) + '" type="button"><i data-feather="bar-chart-2"></i> Report</button>' +
                '</div>';
            els.resultsGrid.appendChild(card);
        });

        refreshIcons();
    }

    function buildScoreBar(label, score) {
        var color = score >= 90 ? "var(--color-primary)" : score >= 70 ? "var(--color-warning)" : "var(--color-danger)";
        return '<div class="score-bar-row">' +
            '<span class="score-bar-label">' + label + '</span>' +
            '<div class="score-bar-track">' +
            '<div class="score-bar-fill" style="width:' + score + '%;background:' + color + '"></div>' +
            '</div>' +
            '<span class="score-bar-value">' + score + '</span>' +
            '</div>';
    }

    function syncResultCheckboxes() {
        els.resultsGrid.querySelectorAll(".result-card-checkbox").forEach(function (cb) {
            var id = parseInt(cb.dataset.id);
            cb.checked = state.selectedIds.has(id);
            var card = cb.closest(".result-card");
            if (card) card.classList.toggle("result-card--selected", cb.checked);
        });
    }

    function syncSelectAllCheckbox() {
        var visible = getFilteredResults();
        if (visible.length === 0) {
            els.selectAllCheckbox.checked = false;
            return;
        }
        var allChecked = visible.every(function (r) { return state.selectedIds.has(r.id); });
        els.selectAllCheckbox.checked = allChecked;
    }

    function updateSelectionBar() {
        var count = state.selectedIds.size;
        if (count > 0) {
            els.selectionBar.style.display = "";
            els.selectionCount.textContent = count + " selected";
        } else {
            els.selectionBar.style.display = "none";
        }
    }

    function exportSelectedPdfs() {
        state.selectedIds.forEach(function (id) {
            window.open("/dashboard/candidate-pdf/" + id, "_blank");
        });
    }

    function openResumePreview(candidateId, name) {
        els.resumePreviewName.textContent = name || "Resume Preview";
        els.resumePreviewIframe.src = "/dashboard/resume-pdf/" + candidateId;
        els.resumePreviewModal.style.display = "";
        refreshIcons();
    }

    function openReportPreview(candidateId, name) {
        els.resumePreviewName.textContent = (name ? name + " – Report" : "Report Preview");
        els.resumePreviewIframe.src = "/dashboard/candidate-pdf/" + candidateId;
        els.resumePreviewModal.style.display = "";
        refreshIcons();
    }

    function closeResumePreview() {
        els.resumePreviewModal.style.display = "none";
        els.resumePreviewIframe.src = "";
    }

    function openInviteModal() {
        if (state.selectedIds.size === 0) {
            window.toast("Select at least one candidate", "error");
            return;
        }
        els.inviteModal.style.display = "";

        if (els.inviteSchedulingLink && !els.inviteSchedulingLink.value) {
            els.inviteSchedulingLink.value = "";
        }

        if (!els.inviteMessage.value) {
            els.inviteMessage.value = els.inviteMessage.dataset.default || '';
        }

        refreshIcons();
    }

    function closeInviteModal() {
        els.inviteModal.style.display = "none";
    }

    function submitInvites() {
        var schedulingLink = els.inviteSchedulingLink ? els.inviteSchedulingLink.value.trim() : "";
        var message = els.inviteMessage.value;

        if (!schedulingLink) {
            window.toast("Please provide a scheduling link", "error");
            return;
        }

        els.inviteSubmitBtn.disabled = true;
        els.inviteSubmitBtn.textContent = "Sending...";

        fetch("/dashboard/send-invites", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                candidate_ids: Array.from(state.selectedIds),
                scheduling_link: schedulingLink,
                message: message
            })
        })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.success) {
                    closeInviteModal();
                    var sentCount = data.results.filter(function (r) { return r.email_sent; }).length;
                    window.toast(sentCount + " invite(s) sent", "success");

                    data.results.forEach(function (r) {
                        var c = state.results.find(function (c) { return c.id === r.id; });
                        if (c) c.status = "invited";
                    });
                    state.selectedIds.clear();
                    applyFilters();
                    updateSelectionBar();
                    setTimeout(function () { goToStep(4); }, 800);
                } else {
                    window.toast(data.error || "Failed to send invites", "error");
                }
            })
            .catch(function () {
                window.toast("Network error sending invites", "error");
            })
            .finally(function () {
                els.inviteSubmitBtn.disabled = false;
                els.inviteSubmitBtn.innerHTML = '<i data-feather="send"></i> Send Invites';
                refreshIcons();
            });
    }

    function bindModals() {
        els.inviteModalClose.addEventListener("click", closeInviteModal);
        els.inviteCancelBtn.addEventListener("click", closeInviteModal);
        els.inviteSubmitBtn.addEventListener("click", submitInvites);
        els.inviteModal.addEventListener("click", function (e) {
            if (e.target === els.inviteModal) closeInviteModal();
        });

        els.resumePreviewClose.addEventListener("click", closeResumePreview);
        els.resumePreviewModal.addEventListener("click", function (e) {
            if (e.target === els.resumePreviewModal) closeResumePreview();
        });

        els.finalDecisionClose.addEventListener("click", closeFinalDecisionModal);
        els.finalDecisionCancel.addEventListener("click", closeFinalDecisionModal);
        els.finalDecisionSubmit.addEventListener("click", submitFinalDecision);
        els.finalDecisionModal.addEventListener("click", function (e) {
            if (e.target === els.finalDecisionModal) closeFinalDecisionModal();
        });

        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape") {
                if (els.resumePreviewModal.style.display !== "none") closeResumePreview();
                if (els.inviteModal.style.display !== "none") closeInviteModal();
                if (els.finalDecisionModal.style.display !== "none") closeFinalDecisionModal();
            }
        });
    }

    function bindStep4() {
        els.step4BackBtn.addEventListener("click", function () {
            goToStep(3);
        });

        els.step4StatusGroups.addEventListener("click", function (e) {
            var hireBtn = e.target.closest(".btn-hire");
            if (hireBtn) {
                openFinalDecisionModal(parseInt(hireBtn.dataset.id), "hire");
                return;
            }

            var rejectBtn = e.target.closest(".btn-no-hire");
            if (rejectBtn) {
                openFinalDecisionModal(parseInt(rejectBtn.dataset.id), "reject");
                return;
            }

            var onboardBtn = e.target.closest(".generate-onboarding-btn");
            if (onboardBtn) {
                window.open("/dashboard/generate-onboarding/" + onboardBtn.dataset.id, "_blank");
                return;
            }

            var nameTrigger = e.target.closest(".resume-preview-trigger");
            if (nameTrigger) {
                openResumePreview(nameTrigger.dataset.id, nameTrigger.dataset.name);
                return;
            }
        });

        els.step4StatusGroups.addEventListener("keydown", function (e) {
            var nameTrigger = e.target.closest(".resume-preview-trigger");
            if (!nameTrigger) return;
            if (e.key === "Enter" || e.key === " " || e.key === "Spacebar") {
                e.preventDefault();
                openResumePreview(nameTrigger.dataset.id, nameTrigger.dataset.name);
            }
        });
    }

    function loadStep4Candidates() {
        var jobId = state.jobId || state.viewingJobId;
        if (!jobId) return;

        fetch("/dashboard/results/" + jobId)
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.success) {
                    renderStep4(data.results);
                }
            })
            .catch(function () {
                window.toast("Could not load candidates", "error");
            });
    }

    function renderStep4(candidates) {
        els.step4StatusGroups.innerHTML = "";

        var invited = candidates.filter(function (c) { return c.status === "invited" || c.status === "interview_done"; });
        var hired = candidates.filter(function (c) { return c.status === "final_hired"; });
        var rejected = candidates.filter(function (c) { return c.status === "final_rejected"; });

        var hasAny = invited.length || hired.length || rejected.length;
        if (!hasAny) {
            els.step4StatusGroups.innerHTML = '<p class="results-empty">No candidates have been invited for interviews yet. Go back to Step 3 to select and invite candidates.</p>';
            return;
        }

        if (invited.length) {
            renderStep4Group("Awaiting Decision", "clipboard", invited, function (r) {
                return '<button class="btn-outline-sm btn-hire" data-id="' + r.id + '" type="button"><i data-feather="user-check"></i> Hire</button>' +
                    '<button class="btn-outline-sm btn-no-hire" data-id="' + r.id + '" type="button"><i data-feather="user-x"></i> No</button>';
            });
        }

        if (hired.length) {
            renderStep4Group("Hired", "award", hired, function (r) {
                return '<button class="btn-primary btn-sm generate-onboarding-btn" data-id="' + r.id + '" type="button"><i data-feather="file-text"></i> Onboarding Doc</button>';
            });
        }

        if (rejected.length) {
            renderStep4Group("Rejected", "x-circle", rejected, function (r) {
                return '';
            });
        }

        refreshIcons();
    }

    function renderStep4Group(title, icon, candidates, actionsBuilder) {
        var group = document.createElement("div");
        group.className = "step4-group";
        group.innerHTML = '<div class="step4-group-header"><i data-feather="' + icon + '"></i><h3>' + title + ' (' + candidates.length + ')</h3></div>';

        var list = document.createElement("div");
        list.className = "results-grid";

        candidates.forEach(function (r) {
            var scoreClass = r.match_score >= 90 ? "green" : r.match_score >= 70 ? "amber" : "red";

            var statusBadgeClass = (r.status === "invited" || r.status === "interview_done") ? "badge-invited" :
                r.status === "final_hired" ? "badge-final-hired" : "badge-final-rejected";
            var statusLabel = (r.status === "invited" || r.status === "interview_done") ? "Invited" :
                r.status === "final_hired" ? "Hired" : "Rejected";

            var interviewInfo = "";
            if (r.interview_at) {
                var d = new Date(r.interview_at);
                interviewInfo = '<span class="result-card-interview">Interview: ' + d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + '</span>';
            }

            var card = document.createElement("div");
            card.className = "result-card";
            card.innerHTML =
                '<div class="result-card-header">' +
                '<div class="result-card-info">' +
                '<i data-feather="user"></i>' +
                '<div class="result-card-text">' +
                '<span class="result-card-name resume-preview-trigger" data-id="' + r.id + '" data-name="' + escapeHtml(r.candidate_name || r.filename) + '" tabindex="0" role="button">' + escapeHtml(r.candidate_name || r.filename) + '</span>' +
                '<span class="result-card-filename">' + escapeHtml(r.candidate_email || r.filename) + '</span>' +
                interviewInfo +
                '</div>' +
                '</div>' +
                '<div style="display:flex;align-items:center;gap:8px;">' +
                '<span class="job-card-badge ' + statusBadgeClass + '">' + statusLabel + '</span>' +
                '<div class="result-score ' + scoreClass + '">' + r.match_score + '</div>' +
                '</div>' +
                '</div>' +
                '<div class="result-card-actions">' +
                actionsBuilder(r) +
                '</div>';

            list.appendChild(card);
        });

        group.appendChild(list);
        els.step4StatusGroups.appendChild(group);
    }

    function openFinalDecisionModal(candidateId, decision) {
        els.finalDecisionId.value = candidateId;
        els.finalDecisionType.value = decision;
        els.finalDecisionTitle.textContent = decision === "hire" ? "Confirm Hire" : "Confirm Rejection";
        els.finalDecisionNotes.value = "";
        els.finalDecisionModal.style.display = "";
        refreshIcons();
    }

    function closeFinalDecisionModal() {
        els.finalDecisionModal.style.display = "none";
    }

    function submitFinalDecision() {
        var candidateId = parseInt(els.finalDecisionId.value);
        var decision = els.finalDecisionType.value;
        var notes = els.finalDecisionNotes.value;

        els.finalDecisionSubmit.disabled = true;
        els.finalDecisionSubmit.textContent = "Saving...";

        fetch("/dashboard/final-decision", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ candidate_id: candidateId, decision: decision, notes: notes })
        })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.success) {
                    closeFinalDecisionModal();
                    var newStatus = decision === "hire" ? "final_hired" : "final_rejected";
                    var c = state.results.find(function (c) { return c.id === candidateId; });
                    if (c) c.status = newStatus;
                    var emailNote = data.email_sent ? " — email sent" : "";
                    window.toast((decision === "hire" ? "Candidate hired" : "Candidate rejected") + emailNote, "success");
                    loadStep4Candidates();
                } else {
                    window.toast(data.error || "Failed to update", "error");
                }
            })
            .catch(function () { window.toast("Network error", "error"); })
            .finally(function () {
                els.finalDecisionSubmit.disabled = false;
                els.finalDecisionSubmit.textContent = "Confirm";
            });
    }

    function restoreDraft() {
        if (!window.__draftJob) return;

        var draft = window.__draftJob;
        state.jobId = draft.id;

        if (draft.status === "completed" && draft.candidates && draft.candidates.length) {
            var hasScored = draft.candidates.some(function (c) { return c.status === "scored"; });
            if (hasScored) {
                state.jobId = null;
                goToStep(1);
                return;
            }
        }

        if (draft.candidates && draft.candidates.length) {
            state.resumes = draft.candidates;
            showWizard();
            goToStep(2);
            renderResumeList();
        } else if (draft.status === "draft") {
            showWizard();
            goToStep(2);
        }
    }

    document.addEventListener("DOMContentLoaded", init);
})();
