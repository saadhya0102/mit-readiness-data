param(
    [string]$Root = "C:\Users\hasto\Demo Projects\speech-debate-college-research",
    [string]$Output = "C:\Users\hasto\Demo Projects\outputs\ab0d060c-0f62-4e15-8025-c59cb48239e6\speech_debate_college_pipeline.xlsx"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-TextValue {
    param($Object, [string]$Property)
    $item = $Object.PSObject.Properties[$Property]
    if ($null -eq $item -or $null -eq $item.Value) {
        return ""
    }
    return ([string]$item.Value).Trim()
}

function Normalize-Key {
    param([string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ""
    }
    $normalized = $Value.ToLowerInvariant()
    $normalized = $normalized -replace "&", " and "
    $normalized = $normalized -replace "\bthe\b", " "
    $normalized = $normalized -replace "\buniversity\b", " university "
    $normalized = $normalized -replace "[^a-z0-9]+", " "
    return ($normalized -replace "\s+", " ").Trim()
}

function Get-StatusScore {
    param([string]$Status)
    switch ($Status.ToLowerInvariant()) {
        "confirmed" { return 4 }
        "probable" { return 3 }
        "ambiguous" { return 2 }
        default { return 1 }
    }
}

function Get-ConfidenceScore {
    param([string]$Confidence)
    switch ($Confidence.ToLowerInvariant()) {
        "high" { return 3 }
        "medium" { return 2 }
        default { return 1 }
    }
}

function Write-Matrix {
    param(
        $Worksheet,
        [int]$StartRow,
        [int]$StartColumn,
        [object[]]$Rows
    )
    $rowList = @($Rows)
    if ($rowList.Count -eq 0) {
        return $null
    }
    $columnCount = @($rowList[0]).Count
    $matrix = [object[,]]::new($rowList.Count, $columnCount)
    for ($r = 0; $r -lt $rowList.Count; $r++) {
        $current = @($rowList[$r])
        for ($c = 0; $c -lt $columnCount; $c++) {
            $matrix[$r, $c] = $current[$c]
        }
    }
    $endRow = $StartRow + $rowList.Count - 1
    $endColumn = $StartColumn + $columnCount - 1
    $range = $Worksheet.Range(
        $Worksheet.Cells.Item($StartRow, $StartColumn),
        $Worksheet.Cells.Item($endRow, $endColumn)
    )
    $range.Value2 = $matrix
    return ,$range
}

function Write-Row {
    param(
        $Worksheet,
        [int]$StartRow,
        [int]$StartColumn,
        [object[]]$Values
    )
    $matrix = [object[,]]::new(1, $Values.Count)
    for ($c = 0; $c -lt $Values.Count; $c++) {
        $matrix[0, $c] = $Values[$c]
    }
    $range = $Worksheet.Range(
        $Worksheet.Cells.Item($StartRow, $StartColumn),
        $Worksheet.Cells.Item($StartRow, $StartColumn + $Values.Count - 1)
    )
    $range.Value2 = $matrix
    return ,$range
}

function Add-ExcelTable {
    param(
        $Worksheet,
        $Range,
        [string]$Name,
        [string]$Style = "TableStyleMedium2"
    )
    $table = $Worksheet.ListObjects.Add(1, $Range, $null, 1)
    $table.Name = $Name
    $table.TableStyle = $Style
    return $table
}

function Set-Title {
    param($Worksheet, [string]$RangeAddress, [string]$Text)
    $range = $Worksheet.Range($RangeAddress)
    $range.Merge()
    $range.Value2 = $Text
    $range.Font.Name = "Aptos Display"
    $range.Font.Size = 22
    $range.Font.Bold = $true
    $range.Font.Color = 0xFFFFFF
    $range.Interior.Color = 0x59391E
    $range.HorizontalAlignment = -4131
    $range.VerticalAlignment = -4108
    $range.RowHeight = 38
}

function Set-SectionHeader {
    param($Range)
    $Range.Font.Name = "Aptos"
    $Range.Font.Bold = $true
    $Range.Font.Color = 0xFFFFFF
    $Range.Interior.Color = 0x866427
    $Range.VerticalAlignment = -4108
}

function Add-Chart {
    param(
        $Worksheet,
        $SourceRange,
        [string]$Title,
        [int]$ChartType,
        [double]$Left,
        [double]$Top,
        [double]$Width,
        [double]$Height,
        [bool]$ShowLegend = $true,
        [string]$CategoryAxisTitle = "",
        [string]$ValueAxisTitle = ""
    )
    $chartObject = $Worksheet.ChartObjects().Add($Left, $Top, $Width, $Height)
    $chartObject.Placement = 3
    $chart = $chartObject.Chart
    $chart.SetSourceData($SourceRange, 2)
    $chart.PlotVisibleOnly = $false
    $chart.ChartType = $ChartType
    $chart.HasTitle = $true
    $chart.ChartTitle.Text = $Title
    $chart.ChartTitle.Format.TextFrame2.TextRange.Font.Name = "Aptos Display"
    $chart.ChartTitle.Format.TextFrame2.TextRange.Font.Size = 14
    $chart.HasLegend = $ShowLegend
    if ($ShowLegend) {
        $chart.Legend.Position = -4107
    }
    if ($ChartType -ne 5) {
        if (-not [string]::IsNullOrWhiteSpace($CategoryAxisTitle)) {
            $categoryAxis = $chart.Axes(1)
            $categoryAxis.HasTitle = $true
            $categoryAxis.AxisTitle.Text = $CategoryAxisTitle
        }
        if (-not [string]::IsNullOrWhiteSpace($ValueAxisTitle)) {
            $valueAxis = $chart.Axes(2)
            $valueAxis.HasTitle = $true
            $valueAxis.AxisTitle.Text = $ValueAxisTitle
        }
    }
    try {
        $chart.ChartArea.Format.Line.ForeColor.RGB = 0xD9D4CC
        $chart.ChartArea.Format.Fill.ForeColor.RGB = 0xFFFFFF
    } catch {}
    return $chart
}

function Add-Link {
    param($Worksheet, $Cell, [string]$Url, [string]$Label)
    if ([string]::IsNullOrWhiteSpace($Url)) {
        return
    }
    $display = if ([string]::IsNullOrWhiteSpace($Label)) { $Url } else { $Label }
    $Cell.Value2 = $display
    $null = $Worksheet.Hyperlinks.Add($Cell, $Url)
}

function Set-ChartSeries {
    param(
        $Chart,
        $CategoryRange,
        [object[]]$Series
    )
    while ($Chart.SeriesCollection().Count -gt 0) {
        $Chart.SeriesCollection(1).Delete()
    }
    foreach ($item in $Series) {
        $newSeries = $Chart.SeriesCollection().NewSeries()
        $newSeries.Name = [string]$item.Name
        $newSeries.XValues = $CategoryRange
        $newSeries.Values = $item.Values
    }
}

$dataRoot = Join-Path $Root "data"
$championFiles = @(
    (Join-Path $dataRoot "nsda_debate_2007_2011.csv"),
    (Join-Path $dataRoot "nsda_debate_2012_2016.csv"),
    (Join-Path $dataRoot "nsda_debate_2017_2021.csv"),
    (Join-Path $dataRoot "nsda_speech_2007_2011.csv"),
    (Join-Path $dataRoot "nsda_speech_2012_2016.csv"),
    (Join-Path $dataRoot "nsda_speech_2017_2021.csv")
)
$rankingFile = Join-Path $dataRoot "forbes_2025_top100.csv"
$aggregateFile = Join-Path $dataRoot "published_aggregate_evidence.csv"
$protocolFile = Join-Path $Root "study_protocol.md"

$requiredFiles = @($championFiles) + @($rankingFile, $aggregateFile, $protocolFile)
foreach ($path in $requiredFiles) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required input is missing: $path"
    }
}

$rankingRows = @(Import-Csv -LiteralPath $rankingFile -Encoding UTF8 | Sort-Object { [int](Get-TextValue $_ "rank") })
if ($rankingRows.Count -ne 100) {
    throw "Ranking file must contain exactly 100 data rows; found $($rankingRows.Count)."
}
$rankValues = @($rankingRows | ForEach-Object { [int](Get-TextValue $_ "rank") })
if ((@($rankValues | Sort-Object -Unique)).Count -ne 100 -or ($rankValues | Measure-Object -Minimum).Minimum -ne 1 -or ($rankValues | Measure-Object -Maximum).Maximum -ne 100) {
    throw "Ranking file must contain each rank from 1 through 100 exactly once."
}

$canonicalMap = @{}
foreach ($row in $rankingRows) {
    $institution = Get-TextValue $row "institution"
    $canonical = Get-TextValue $row "canonical_name"
    if ([string]::IsNullOrWhiteSpace($canonical)) {
        $canonical = $institution
    }
    $names = New-Object System.Collections.ArrayList
    $null = $names.Add($institution)
    $null = $names.Add($canonical)
    $aliases = Get-TextValue $row "aliases"
    if (-not [string]::IsNullOrWhiteSpace($aliases)) {
        foreach ($alias in ($aliases -split "[;|]")) {
            $null = $names.Add($alias.Trim())
        }
    }
    foreach ($name in $names) {
        $key = Normalize-Key ([string]$name)
        if (-not [string]::IsNullOrWhiteSpace($key)) {
            $canonicalMap[$key] = $canonical
        }
    }
}

$manualAliases = @{
    "mit" = "Massachusetts Institute of Technology"
    "massachusetts institute technology" = "Massachusetts Institute of Technology"
    "upenn" = "University of Pennsylvania"
    "penn" = "University of Pennsylvania"
    "u penn" = "University of Pennsylvania"
    "uchicago" = "University of Chicago"
    "u chicago" = "University of Chicago"
    "university southern california" = "University of Southern California"
    "usc" = "University of Southern California"
    "ohio state university" = "The Ohio State University"
    "osu" = "The Ohio State University"
}
foreach ($alias in $manualAliases.Keys) {
    $target = $manualAliases[$alias]
    $targetKey = Normalize-Key $target
    if ($canonicalMap.ContainsKey($targetKey)) {
        $target = $canonicalMap[$targetKey]
    }
    $canonicalMap[(Normalize-Key $alias)] = $target
}

$allRows = New-Object System.Collections.ArrayList
$requiredChampionColumns = @(
    "sample_id", "competition", "competition_level", "event", "year", "placement",
    "participant_name", "high_school", "state_or_country", "result_source_url", "college",
    "college_source_url", "college_source_type", "college_match_status",
    "college_match_confidence", "match_notes"
)
foreach ($file in $championFiles) {
    $fileRows = @(Import-Csv -LiteralPath $file -Encoding UTF8)
    if ($fileRows.Count -eq 0) {
        throw "Champion file has no data rows: $file"
    }
    $presentColumns = @($fileRows[0].PSObject.Properties.Name)
    foreach ($column in $requiredChampionColumns) {
        if ($column -notin $presentColumns) {
            throw "Champion file $file is missing required column '$column'."
        }
    }
    foreach ($row in $fileRows) {
        $event = Get-TextValue $row "event"
        $discipline = if ($event -match "(?i)debate|lincoln|policy|public forum") { "Debate" } else { "Speech" }
        $participant = Get-TextValue $row "participant_name"
        $school = Get-TextValue $row "high_school"
        $college = Get-TextValue $row "college"
        if ($college -match "^(?i:unknown|not found|n/?a)$") {
            $college = ""
        }
        $collegeKey = Normalize-Key $college
        $canonical = $college
        if (-not [string]::IsNullOrWhiteSpace($collegeKey) -and $canonicalMap.ContainsKey($collegeKey)) {
            $canonical = $canonicalMap[$collegeKey]
        }
        $personKey = "$(Normalize-Key $participant)|$(Normalize-Key $school)"
        $clean = [pscustomobject]@{
            sample_id = Get-TextValue $row "sample_id"
            competition = Get-TextValue $row "competition"
            competition_level = Get-TextValue $row "competition_level"
            event = $event
            year = [int](Get-TextValue $row "year")
            placement = Get-TextValue $row "placement"
            participant_name = $participant
            high_school = $school
            state_or_country = Get-TextValue $row "state_or_country"
            result_source_url = Get-TextValue $row "result_source_url"
            college = $college
            college_canonical = $canonical
            college_source_url = Get-TextValue $row "college_source_url"
            college_source_type = Get-TextValue $row "college_source_type"
            college_match_status = (Get-TextValue $row "college_match_status").ToLowerInvariant()
            college_match_confidence = (Get-TextValue $row "college_match_confidence").ToLowerInvariant()
            match_notes = Get-TextValue $row "match_notes"
            discipline = $discipline
            person_key = $personKey
        }
        $null = $allRows.Add($clean)
    }
}

if ($allRows.Count -lt 125) {
    throw "Expected at least 125 champion participant-event rows; found $($allRows.Count)."
}

$duplicateSampleIds = @($allRows | Group-Object sample_id | Where-Object { $_.Count -gt 1 })
if ($duplicateSampleIds.Count -gt 0) {
    throw "Duplicate sample_id values found: $($duplicateSampleIds.Name -join ', ')"
}
$allowedStatuses = @("confirmed", "probable", "ambiguous", "unknown")
$allowedConfidence = @("high", "medium", "low")
foreach ($row in $allRows) {
    if ($row.college_match_status -notin $allowedStatuses) {
        throw "Invalid match status '$($row.college_match_status)' in $($row.sample_id)."
    }
    if ($row.college_match_confidence -notin $allowedConfidence) {
        throw "Invalid confidence '$($row.college_match_confidence)' in $($row.sample_id)."
    }
    if ([string]::IsNullOrWhiteSpace($row.result_source_url)) {
        throw "Missing tournament result URL in $($row.sample_id)."
    }
    if ($row.college_match_status -in @("confirmed", "probable") -and (
        [string]::IsNullOrWhiteSpace($row.college) -or
        [string]::IsNullOrWhiteSpace($row.college_source_url)
    )) {
        throw "Matched record $($row.sample_id) lacks a college or source URL."
    }
}
$expectedEvents = @(
    "Lincoln-Douglas Debate",
    "Policy Debate",
    "Public Forum Debate",
    "International Extemporaneous Speaking",
    "United States Extemporaneous Speaking",
    "Original Oratory",
    "Duo Interpretation"
)
foreach ($year in 2007..2021) {
    foreach ($event in $expectedEvents) {
        $eventRows = @(if ($event -eq "Duo Interpretation") {
            $allRows | Where-Object { $_.year -eq $year -and $_.event -like "Duo Interpretation*" }
        } else {
            $allRows | Where-Object { $_.year -eq $year -and $_.event -eq $event }
        })
        if ($eventRows.Count -eq 0) {
            throw "Missing expected champion record for $year / $event."
        }
    }
}

$uniqueRows = New-Object System.Collections.ArrayList
$personGroups = @($allRows | Group-Object person_key | Sort-Object { ($_.Group | Select-Object -First 1).participant_name })
$personIndex = 1
foreach ($group in $personGroups) {
    $records = @($group.Group)
    $best = @(
        $records | Sort-Object `
            @{ Expression = { Get-StatusScore $_.college_match_status }; Descending = $true }, `
            @{ Expression = { Get-ConfidenceScore $_.college_match_confidence }; Descending = $true }, `
            @{ Expression = { if ([string]::IsNullOrWhiteSpace($_.college_source_url)) { 0 } else { 1 } }; Descending = $true }, `
            @{ Expression = { $_.year }; Descending = $true }
    )[0]
    $confirmedColleges = @(
        $records |
            Where-Object { $_.college_match_status -eq "confirmed" -and -not [string]::IsNullOrWhiteSpace($_.college_canonical) } |
            Select-Object -ExpandProperty college_canonical -Unique
    )
    $conflict = if ($confirmedColleges.Count -gt 1) { "Conflicting confirmed college records: $($confirmedColleges -join '; ')." } else { "" }
    $years = @($records | Select-Object -ExpandProperty year | Sort-Object -Unique)
    $events = @($records | Select-Object -ExpandProperty event | Sort-Object -Unique)
    $disciplines = @($records | Select-Object -ExpandProperty discipline | Sort-Object -Unique)
    $unique = [pscustomobject]@{
        person_id = "P{0:D3}" -f $personIndex
        participant_name = $best.participant_name
        high_school = $best.high_school
        state_or_country = $best.state_or_country
        first_year = ($years | Measure-Object -Minimum).Minimum
        last_year = ($years | Measure-Object -Maximum).Maximum
        performance_rows = $records.Count
        disciplines = $disciplines -join "; "
        events = $events -join "; "
        college = $best.college
        college_canonical = $best.college_canonical
        college_source_url = $best.college_source_url
        college_source_type = $best.college_source_type
        college_match_status = $best.college_match_status
        college_match_confidence = $best.college_match_confidence
        match_notes = (($best.match_notes, $conflict | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join " ")
        result_source_url = $best.result_source_url
    }
    $null = $uniqueRows.Add($unique)
    $personIndex++
}

$aggregateRows = @(Import-Csv -LiteralPath $aggregateFile -Encoding UTF8)
if ($aggregateRows.Count -lt 4) {
    throw "Published aggregate evidence file is unexpectedly small: $($aggregateRows.Count) rows."
}

$outputDirectory = Split-Path -Parent $Output
if (-not (Test-Path -LiteralPath $outputDirectory)) {
    $null = New-Item -ItemType Directory -Path $outputDirectory -Force
}
$pdfOutput = [System.IO.Path]::ChangeExtension($Output, ".pdf")

$excel = $null
$workbook = $null
try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $excel.ScreenUpdating = $false
    $workbook = $excel.Workbooks.Add()

    $sheetNames = @(
        "Read Me",
        "Dashboard",
        "Tier Analysis",
        "College Destinations",
        "Unique Champions",
        "Champion Records",
        "Published Evidence",
        "Rankings",
        "Source Audit",
        "Methods"
    )

    $firstSheet = $workbook.Worksheets.Item(1)
    $firstSheet.Name = $sheetNames[0]
    while ($workbook.Worksheets.Count -gt 1) {
        $workbook.Worksheets.Item($workbook.Worksheets.Count).Delete()
    }
    for ($i = 1; $i -lt $sheetNames.Count; $i++) {
        $newSheet = $workbook.Worksheets.Add([Type]::Missing, $workbook.Worksheets.Item($workbook.Worksheets.Count))
        $newSheet.Name = $sheetNames[$i]
    }

    $readMe = $workbook.Worksheets.Item("Read Me")
    Set-Title $readMe "A1:H1" "Speech/Debate to College Destination Study"
    $readMe.Range("A3:H3").Merge()
    $readMe.Range("A3").Value2 = "A source-audited, descriptive study of NSDA national champions from 2007-2021"
    $readMe.Range("A3").Font.Size = 13
    $readMe.Range("A3").Font.Color = 0x735B45
    $null = Write-Row $readMe 5 1 @("Workbook section", "What it contains")
    Set-SectionHeader $readMe.Range("A5:B5")
    $readMeRows = @(
        @("Dashboard", "Headline coverage and cumulative T1/T10/T25/T50/T100 results with charts."),
        @("Tier Analysis", "Counts, denominators, lower/upper bounds, discipline cuts, and sensitivity analysis."),
        @("College Destinations", "Observed destinations and current Forbes rank classification."),
        @("Unique Champions", "Primary participant-level analytical file; repeat winners appear once."),
        @("Champion Records", "Participant-event-year source records; repeat winners remain repeated."),
        @("Published Evidence", "Separate aggregate studies; not pooled with the champion cohort."),
        @("Rankings", "Forbes 2025-2026 rank map and source metadata."),
        @("Source Audit", "Participant identity evidence, result URLs, college URLs, and match notes."),
        @("Methods", "Study protocol, missing-data rules, biases, and interpretation limits.")
    )
    $readRange = Write-Matrix $readMe 6 1 $readMeRows
    $readRange.WrapText = $true
    $readMe.Range("A17:H17").Merge()
    $readMe.Range("A17").Value2 = "What this can and cannot establish"
    Set-SectionHeader $readMe.Range("A17:H17")
    $readMe.Range("A18:H21").Merge()
    $readMe.Range("A18").Value2 = "This workbook describes publicly documented college destinations among a selected group of national champions. It does not show that speech or debate caused admission, does not estimate admissions odds, and does not measure performance in college. Selective-college destinations may be easier to verify publicly, so missingness can bias the observed rates upward. Use the lower and upper bounds, source-status cuts, and published comparison evidence together."
    $readMe.Range("A18").WrapText = $true
    $readMe.Range("A18").VerticalAlignment = -4160
    $readMe.Range("A23:H23").Merge()
    $readMe.Range("A23").Value2 = "Recommended presentation sentence"
    Set-SectionHeader $readMe.Range("A23:H23")
    $readMe.Range("A24:H26").Merge()
    $readMe.Range("A24").Value2 = '"In this source-matched cohort of NSDA national champions, selective-college attendance is common. The pattern is descriptive and compatible with several explanations, including prior academic strength, school and coaching resources, self-selection, and admissions recognition of debate-related achievement."'
    $readMe.Range("A24").WrapText = $true
    $readMe.Columns("A").ColumnWidth = 24
    $readMe.Columns("B").ColumnWidth = 72
    $readMe.Columns("C:H").ColumnWidth = 12
    $readMe.Rows("18:26").RowHeight = 24
    $readMe.Range("A1:H30").Font.Name = "Aptos"

    $rankings = $workbook.Worksheets.Item("Rankings")
    Set-Title $rankings "A1:I1" "Forbes 2025-2026 Top 100 Rank Map"
    $rankingHeaders = @("canonical_name", "rank", "institution", "aliases", "ranking_name", "ranking_year", "source_url", "source_type", "notes")
    $rankingMatrix = New-Object System.Collections.ArrayList
    $null = $rankingMatrix.Add([object[]]$rankingHeaders)
    foreach ($row in $rankingRows) {
        $canonical = Get-TextValue $row "canonical_name"
        if ([string]::IsNullOrWhiteSpace($canonical)) {
            $canonical = Get-TextValue $row "institution"
        }
        $null = $rankingMatrix.Add([object[]]@(
            $canonical,
            [int](Get-TextValue $row "rank"),
            (Get-TextValue $row "institution"),
            (Get-TextValue $row "aliases"),
            (Get-TextValue $row "ranking_name"),
            (Get-TextValue $row "ranking_year"),
            (Get-TextValue $row "source_url"),
            (Get-TextValue $row "source_type"),
            (Get-TextValue $row "notes")
        ))
    }
    $rankingRange = Write-Matrix $rankings 3 1 $rankingMatrix
    $null = Add-ExcelTable $rankings $rankingRange "RankingsTable"
    $rankings.Range("B4:B103").NumberFormat = "0"
    $rankings.Columns("A").ColumnWidth = 34
    $rankings.Columns("B").ColumnWidth = 9
    $rankings.Columns("C").ColumnWidth = 34
    $rankings.Columns("D").ColumnWidth = 35
    $rankings.Columns("E:F").ColumnWidth = 18
    $rankings.Columns("G").ColumnWidth = 55
    $rankings.Columns("H").ColumnWidth = 18
    $rankings.Columns("I").ColumnWidth = 44
    $rankings.Range("A3:I103").WrapText = $true

    $uniqueSheet = $workbook.Worksheets.Item("Unique Champions")
    Set-Title $uniqueSheet "A1:AA1" "Unique NSDA National Champions: Primary Analytical File"
    $uniqueHeaders = @(
        "person_id", "participant_name", "high_school", "state_or_country", "first_year", "last_year",
        "performance_rows", "disciplines", "events", "college", "college_canonical", "college_source_url",
        "college_source_type", "college_match_status", "college_match_confidence", "match_notes",
        "forbes_rank", "rank_bin", "is_mit", "t1", "t10", "t25", "t50", "t100",
        "primary_confirmed", "sensitivity_confirmed_probable", "result_source_url"
    )
    $uniqueMatrix = New-Object System.Collections.ArrayList
    $null = $uniqueMatrix.Add([object[]]$uniqueHeaders)
    foreach ($row in $uniqueRows) {
        $null = $uniqueMatrix.Add([object[]]@(
            $row.person_id, $row.participant_name, $row.high_school, $row.state_or_country,
            [int]$row.first_year, [int]$row.last_year, [int]$row.performance_rows, $row.disciplines,
            $row.events, $row.college, $row.college_canonical, $row.college_source_url,
            $row.college_source_type, $row.college_match_status, $row.college_match_confidence,
            $row.match_notes, "", "", "", "", "", "", "", "", "", "", $row.result_source_url
        ))
    }
    $uniqueRange = Write-Matrix $uniqueSheet 3 1 $uniqueMatrix
    $uniqueEnd = 3 + $uniqueRows.Count
    for ($r = 4; $r -le $uniqueEnd; $r++) {
        $uniqueSheet.Cells.Item($r, 17).Formula = "=IFERROR(INDEX(Rankings!`$B`$4:`$B`$103,MATCH(K$r,Rankings!`$A`$4:`$A`$103,0)),`"`")"
        $uniqueSheet.Cells.Item($r, 18).Formula = "=IF(J$r=`"`",`"Unknown`",IF(OR(K$r=`"University of Oxford`",K$r=`"McGill University`",K$r=`"University of Cambridge`",K$r=`"London School of Economics and Political Science`"),`"Non-U.S.`",IF(Q$r=`"`",`"U.S. >100 / unranked`",IF(Q$r=1,`"Rank 1`",IF(Q$r<=10,`"Ranks 2-10`",IF(Q$r<=25,`"Ranks 11-25`",IF(Q$r<=50,`"Ranks 26-50`",`"Ranks 51-100`")))))))"
        $uniqueSheet.Cells.Item($r, 19).Formula = "=--(K$r=`"Massachusetts Institute of Technology`")"
        $uniqueSheet.Cells.Item($r, 20).Formula = "=--(Q$r=1)"
        $uniqueSheet.Cells.Item($r, 21).Formula = "=--(AND(ISNUMBER(Q$r),Q$r<=10))"
        $uniqueSheet.Cells.Item($r, 22).Formula = "=--(AND(ISNUMBER(Q$r),Q$r<=25))"
        $uniqueSheet.Cells.Item($r, 23).Formula = "=--(AND(ISNUMBER(Q$r),Q$r<=50))"
        $uniqueSheet.Cells.Item($r, 24).Formula = "=--(AND(ISNUMBER(Q$r),Q$r<=100))"
        $uniqueSheet.Cells.Item($r, 25).Formula = "=--(N$r=`"confirmed`")"
        $uniqueSheet.Cells.Item($r, 26).Formula = "=--(OR(N$r=`"confirmed`",N$r=`"probable`"))"
    }
    $null = Add-ExcelTable $uniqueSheet $uniqueRange "UniqueChampionsTable"
    $uniqueSheet.Range("E4:G$uniqueEnd").NumberFormat = "0"
    $uniqueSheet.Range("Q4:Z$uniqueEnd").NumberFormat = "0"
    $uniqueSheet.Columns("A").ColumnWidth = 10
    $uniqueSheet.Columns("B:D").ColumnWidth = 23
    $uniqueSheet.Columns("E:G").ColumnWidth = 12
    $uniqueSheet.Columns("H:I").ColumnWidth = 26
    $uniqueSheet.Columns("J:K").ColumnWidth = 30
    $uniqueSheet.Columns("L").ColumnWidth = 50
    $uniqueSheet.Columns("M:O").ColumnWidth = 18
    $uniqueSheet.Columns("P").ColumnWidth = 70
    $uniqueSheet.Columns("Q:Z").ColumnWidth = 13
    $uniqueSheet.Columns("AA").ColumnWidth = 50
    $uniqueSheet.Range("A3:AA$uniqueEnd").WrapText = $true

    $recordsSheet = $workbook.Worksheets.Item("Champion Records")
    Set-Title $recordsSheet "A1:AA1" "Participant-Event-Year Champion Records"
    $recordHeaders = @(
        "sample_id", "competition", "event", "year", "placement", "participant_name", "high_school",
        "state_or_country", "result_source_url", "college", "college_canonical", "college_source_url",
        "college_source_type", "college_match_status", "college_match_confidence", "match_notes",
        "discipline", "person_key", "forbes_rank", "rank_bin", "is_mit", "t1", "t10", "t25", "t50",
        "t100", "primary_confirmed"
    )
    $recordMatrix = New-Object System.Collections.ArrayList
    $null = $recordMatrix.Add([object[]]$recordHeaders)
    foreach ($row in $allRows) {
        $null = $recordMatrix.Add([object[]]@(
            $row.sample_id, $row.competition, $row.event, [int]$row.year, $row.placement,
            $row.participant_name, $row.high_school, $row.state_or_country, $row.result_source_url,
            $row.college, $row.college_canonical, $row.college_source_url, $row.college_source_type,
            $row.college_match_status, $row.college_match_confidence, $row.match_notes,
            $row.discipline, $row.person_key, "", "", "", "", "", "", "", "", ""
        ))
    }
    $recordRange = Write-Matrix $recordsSheet 3 1 $recordMatrix
    $recordEnd = 3 + $allRows.Count
    for ($r = 4; $r -le $recordEnd; $r++) {
        $recordsSheet.Cells.Item($r, 19).Formula = "=IFERROR(INDEX(Rankings!`$B`$4:`$B`$103,MATCH(K$r,Rankings!`$A`$4:`$A`$103,0)),`"`")"
        $recordsSheet.Cells.Item($r, 20).Formula = "=IF(J$r=`"`",`"Unknown`",IF(OR(K$r=`"University of Oxford`",K$r=`"McGill University`",K$r=`"University of Cambridge`",K$r=`"London School of Economics and Political Science`"),`"Non-U.S.`",IF(S$r=`"`",`"U.S. >100 / unranked`",IF(S$r=1,`"Rank 1`",IF(S$r<=10,`"Ranks 2-10`",IF(S$r<=25,`"Ranks 11-25`",IF(S$r<=50,`"Ranks 26-50`",`"Ranks 51-100`")))))))"
        $recordsSheet.Cells.Item($r, 21).Formula = "=--(K$r=`"Massachusetts Institute of Technology`")"
        $recordsSheet.Cells.Item($r, 22).Formula = "=--(S$r=1)"
        $recordsSheet.Cells.Item($r, 23).Formula = "=--(AND(ISNUMBER(S$r),S$r<=10))"
        $recordsSheet.Cells.Item($r, 24).Formula = "=--(AND(ISNUMBER(S$r),S$r<=25))"
        $recordsSheet.Cells.Item($r, 25).Formula = "=--(AND(ISNUMBER(S$r),S$r<=50))"
        $recordsSheet.Cells.Item($r, 26).Formula = "=--(AND(ISNUMBER(S$r),S$r<=100))"
        $recordsSheet.Cells.Item($r, 27).Formula = "=--(N$r=`"confirmed`")"
    }
    $null = Add-ExcelTable $recordsSheet $recordRange "ChampionRecordsTable"
    $recordsSheet.Range("D4:D$recordEnd").NumberFormat = "0"
    $recordsSheet.Range("S4:AA$recordEnd").NumberFormat = "0"
    $recordsSheet.Columns("A").ColumnWidth = 22
    $recordsSheet.Columns("B:C").ColumnWidth = 25
    $recordsSheet.Columns("D:E").ColumnWidth = 12
    $recordsSheet.Columns("F:H").ColumnWidth = 23
    $recordsSheet.Columns("I").ColumnWidth = 50
    $recordsSheet.Columns("J:K").ColumnWidth = 30
    $recordsSheet.Columns("L").ColumnWidth = 50
    $recordsSheet.Columns("M:O").ColumnWidth = 18
    $recordsSheet.Columns("P").ColumnWidth = 70
    $recordsSheet.Columns("Q:AA").ColumnWidth = 14
    $recordsSheet.Range("A3:AA$recordEnd").WrapText = $true

    $dashboard = $workbook.Worksheets.Item("Dashboard")
    Set-Title $dashboard "A1:Q1" "National Champion College Destinations"
    $dashboard.Range("A2:Q2").Merge()
    $dashboard.Range("A2").Value2 = "Primary unit: unique participant | Main estimate: confirmed public matches | Tiers: current Forbes 2025-2026"
    $dashboard.Range("A2").Font.Color = 0x735B45
    $dashboard.Range("A3:Q3").Merge()
    $dashboard.Range("A3").Value2 = "Descriptive only; no causal inference. Public-destination missingness may be non-random, and the displayed bounds are sensitivity limits."
    $dashboard.Range("A3").Font.Bold = $true
    $dashboard.Range("A3").Font.Color = 0x59391E
    $dashboard.Range("A3").Interior.Color = 0xEAF3F8
    $dashboard.Range("A3").WrapText = $true
    $dashboard.Range("A3").RowHeight = 24
    $dashboard.Range("A4:B4").Merge()
    $dashboard.Range("D4:E4").Merge()
    $dashboard.Range("G4:H4").Merge()
    $dashboard.Range("J4:K4").Merge()
    $dashboard.Range("A4").Value2 = "Unique champions"
    $dashboard.Range("D4").Value2 = "Confirmed destinations"
    $dashboard.Range("G4").Value2 = "Confirmed + probable"
    $dashboard.Range("J4").Value2 = "Confirmed coverage"
    foreach ($address in @("A4:B4", "D4:E4", "G4:H4", "J4:K4")) {
        Set-SectionHeader $dashboard.Range($address)
    }
    $dashboard.Range("A5:B6").Merge()
    $dashboard.Range("D5:E6").Merge()
    $dashboard.Range("G5:H6").Merge()
    $dashboard.Range("J5:K6").Merge()
    $dashboard.Range("A5").FormulaR1C1 = "=COUNTA('Unique Champions'!R4C1:R${uniqueEnd}C1)"
    $dashboard.Range("D5").FormulaR1C1 = "=SUM('Unique Champions'!R4C25:R${uniqueEnd}C25)"
    $dashboard.Range("G5").FormulaR1C1 = "=SUM('Unique Champions'!R4C26:R${uniqueEnd}C26)"
    $dashboard.Range("J5").FormulaR1C1 = "=R5C4/R5C1"
    $dashboard.Range("A5:K6").Font.Size = 20
    $dashboard.Range("A5:K6").Font.Bold = $true
    $dashboard.Range("A5:K6").HorizontalAlignment = -4108
    $dashboard.Range("A5:K6").VerticalAlignment = -4108
    $dashboard.Range("J5").NumberFormat = "0.0%"

    $tierHeaders = @("Tier", "Confirmed count", "Known-destination rate", "All-champion lower bound", "Nonconfirmed upper bound")
    $tierRows = @("MIT", "T1", "T10", "T25", "T50", "T100")
    $tierFlags = @(19, 20, 21, 22, 23, 24)
    $null = Write-Row $dashboard 9 1 $tierHeaders
    Set-SectionHeader $dashboard.Range("A9:E9")
    $dashboard.Range("A9:E9").WrapText = $true
    $dashboard.Rows.Item(9).RowHeight = 30
    for ($i = 0; $i -lt $tierRows.Count; $i++) {
        $rowNumber = 10 + $i
        $flagColumn = $tierFlags[$i]
        $dashboard.Cells.Item($rowNumber, 1).Value2 = $tierRows[$i]
        $dashboard.Cells.Item($rowNumber, 2).FormulaR1C1 = "=SUMIFS('Unique Champions'!R4C${flagColumn}:R${uniqueEnd}C${flagColumn},'Unique Champions'!R4C25:R${uniqueEnd}C25,1)"
        $dashboard.Cells.Item($rowNumber, 3).FormulaR1C1 = "=IFERROR(RC[-1]/R5C4,0)"
        $dashboard.Cells.Item($rowNumber, 4).FormulaR1C1 = "=IFERROR(RC[-2]/R5C1,0)"
        $dashboard.Cells.Item($rowNumber, 5).FormulaR1C1 = "=IFERROR((RC[-3]+(R5C1-R5C4))/R5C1,0)"
    }
    $dashboard.Range("C10:E15").NumberFormat = "0.0%"
    $dashboard.Range("A9:E15").Borders.LineStyle = 1
    $dashboard.Range("A16:E16").Merge()
    $dashboard.Range("A16").Value2 = "MIT and T1 are identical here because Forbes ranks MIT #1."
    $dashboard.Range("A16").Font.Italic = $true
    $dashboard.Range("A16").Font.Color = 0x735B45

    $disciplineHeaders = @("Discipline", "Unique n", "Coverage", "T10", "T25", "T50", "T100")
    $null = Write-Row $dashboard 18 1 $disciplineHeaders
    Set-SectionHeader $dashboard.Range("A18:G18")
    $dashboard.Range("A18:G18").WrapText = $true
    $disciplines = @("Debate", "Speech")
    for ($i = 0; $i -lt $disciplines.Count; $i++) {
        $rowNumber = 19 + $i
        $label = $disciplines[$i]
        $dashboard.Cells.Item($rowNumber, 1).Value2 = $label
        $dashboard.Cells.Item($rowNumber, 2).FormulaR1C1 = "=COUNTIF('Unique Champions'!R4C8:R${uniqueEnd}C8,`"*$label*`")"
        $dashboard.Cells.Item($rowNumber, 3).FormulaR1C1 = "=COUNTIFS('Unique Champions'!R4C8:R${uniqueEnd}C8,`"*$label*`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)/RC[-1]"
        $dashboard.Cells.Item($rowNumber, 4).FormulaR1C1 = "=SUMIFS('Unique Champions'!R4C21:R${uniqueEnd}C21,'Unique Champions'!R4C8:R${uniqueEnd}C8,`"*$label*`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)/COUNTIFS('Unique Champions'!R4C8:R${uniqueEnd}C8,`"*$label*`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)"
        $dashboard.Cells.Item($rowNumber, 5).FormulaR1C1 = "=SUMIFS('Unique Champions'!R4C22:R${uniqueEnd}C22,'Unique Champions'!R4C8:R${uniqueEnd}C8,`"*$label*`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)/COUNTIFS('Unique Champions'!R4C8:R${uniqueEnd}C8,`"*$label*`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)"
        $dashboard.Cells.Item($rowNumber, 6).FormulaR1C1 = "=SUMIFS('Unique Champions'!R4C23:R${uniqueEnd}C23,'Unique Champions'!R4C8:R${uniqueEnd}C8,`"*$label*`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)/COUNTIFS('Unique Champions'!R4C8:R${uniqueEnd}C8,`"*$label*`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)"
        $dashboard.Cells.Item($rowNumber, 7).FormulaR1C1 = "=SUMIFS('Unique Champions'!R4C24:R${uniqueEnd}C24,'Unique Champions'!R4C8:R${uniqueEnd}C8,`"*$label*`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)/COUNTIFS('Unique Champions'!R4C8:R${uniqueEnd}C8,`"*$label*`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)"
    }
    $dashboard.Range("C19:G20").NumberFormat = "0.0%"
    $dashboard.Range("A18:G20").Borders.LineStyle = 1

    $probableUniqueCount = @($uniqueRows | Where-Object { $_.college_match_status -eq "probable" }).Count
    $ambiguousUniqueCount = @($uniqueRows | Where-Object { $_.college_match_status -eq "ambiguous" }).Count
    $unknownUniqueCount = @($uniqueRows | Where-Object { $_.college_match_status -eq "unknown" }).Count
    $binHeaders = @("Non-overlapping bin", "Unique champions")
    $bins = @(
        "Rank 1",
        "Ranks 2-10",
        "Ranks 11-25",
        "Ranks 26-50",
        "Ranks 51-100",
        "U.S. >100 / unranked",
        "Non-U.S.",
        "Not confirmed ($probableUniqueCount probable, $ambiguousUniqueCount ambiguous, $unknownUniqueCount unknown)"
    )
    $null = Write-Row $dashboard 24 1 $binHeaders
    Set-SectionHeader $dashboard.Range("A24:B24")
    $dashboard.Range("A24:B24").WrapText = $true
    for ($i = 0; $i -lt 7; $i++) {
        $rowNumber = 25 + $i
        $dashboard.Cells.Item($rowNumber, 1).Value2 = $bins[$i]
        $dashboard.Cells.Item($rowNumber, 2).FormulaR1C1 = "=COUNTIFS('Unique Champions'!R4C18:R${uniqueEnd}C18,RC[-1],'Unique Champions'!R4C25:R${uniqueEnd}C25,1)"
    }
    $dashboard.Cells.Item(32, 1).Value2 = $bins[7]
    $dashboard.Cells.Item(32, 2).FormulaR1C1 = "=R5C1-R5C4"
    $dashboard.Range("A24:B32").Borders.LineStyle = 1
    $dashboard.Range("A25:A32").WrapText = $true

    $rankedCollegeGroups = @(
        $uniqueRows |
            Where-Object { $_.college_match_status -eq "confirmed" -and -not [string]::IsNullOrWhiteSpace($_.college_canonical) } |
            Group-Object college_canonical |
            Sort-Object @{ Expression = { $_.Count }; Descending = $true }, @{ Expression = { $_.Name }; Descending = $false }
    )
    $topTen = @($rankedCollegeGroups | Select-Object -First 10)
    $topCutoff = if ($topTen.Count -gt 0) { [int]$topTen[-1].Count } else { 0 }
    $topColleges = @($rankedCollegeGroups | Where-Object { $_.Count -ge $topCutoff })
    $null = Write-Row $dashboard 24 4 @("Frequent destination (ties included)", "Unique champions")
    Set-SectionHeader $dashboard.Range("D24:E24")
    $dashboard.Range("D24:E24").WrapText = $true
    $topStart = 25
    $topEnd = 24
    foreach ($collegeGroup in $topColleges) {
        $dashboard.Cells.Item($topStart, 4).Value2 = $collegeGroup.Name
        $dashboard.Cells.Item($topStart, 5).Value2 = [int]$collegeGroup.Count
        $topEnd = $topStart
        $topStart++
    }
    if ($topEnd -ge 25) {
        $dashboard.Range("D24:E$topEnd").Borders.LineStyle = 1
        $dashboard.Range("D25:D$topEnd").WrapText = $true
    }

    $null = Write-Row $dashboard 24 7 @("Match status", "Unique champions")
    Set-SectionHeader $dashboard.Range("G24:H24")
    $dashboard.Range("G24:H24").WrapText = $true
    $dashboard.Rows.Item(24).RowHeight = 30
    $statuses = @("confirmed", "probable", "ambiguous", "unknown")
    for ($i = 0; $i -lt $statuses.Count; $i++) {
        $rowNumber = 25 + $i
        $dashboard.Cells.Item($rowNumber, 7).Value2 = $statuses[$i]
        $dashboard.Cells.Item($rowNumber, 8).FormulaR1C1 = "=COUNTIF('Unique Champions'!R4C14:R${uniqueEnd}C14,RC[-1])"
    }
    $dashboard.Range("G24:H28").Borders.LineStyle = 1

    $null = Write-Row $dashboard 9 24 @("Tier", "Known-destination rate", "All-champion lower bound", "Nonconfirmed upper bound")
    for ($r = 10; $r -le 15; $r++) {
        $dashboard.Cells.Item($r, 24).Formula = "=A$r"
        $dashboard.Cells.Item($r, 25).Formula = "=C$r"
        $dashboard.Cells.Item($r, 26).Formula = "=D$r"
        $dashboard.Cells.Item($r, 27).Formula = "=E$r"
    }
    $null = Write-Row $dashboard 18 24 @("Discipline", "T10", "T25", "T50", "T100")
    for ($r = 19; $r -le 20; $r++) {
        $dashboard.Cells.Item($r, 24).Formula = "=A$r"
        $dashboard.Cells.Item($r, 25).Formula = "=D$r"
        $dashboard.Cells.Item($r, 26).Formula = "=E$r"
        $dashboard.Cells.Item($r, 27).Formula = "=F$r"
        $dashboard.Cells.Item($r, 28).Formula = "=G$r"
    }
    $tierSource = $dashboard.Range("X9:AA15")
    $tierChart = Add-Chart $dashboard $tierSource "Cumulative Selective-College Rates and Missing-Data Bounds" 51 780 135 690 285 $true -CategoryAxisTitle "Ranking cutoff" -ValueAxisTitle "Unique champions (%)"
    Set-ChartSeries $tierChart $dashboard.Range("X10:X15") @(
        [pscustomobject]@{ Name = "Known-destination rate"; Values = $dashboard.Range("Y10:Y15") },
        [pscustomobject]@{ Name = "All-champion lower bound"; Values = $dashboard.Range("Z10:Z15") },
        [pscustomobject]@{ Name = "Nonconfirmed upper bound"; Values = $dashboard.Range("AA10:AA15") }
    )
    $tierChart.Axes(2).TickLabels.NumberFormat = "0%"
    $disciplineSource = $dashboard.Range("X18:AB20")
    $disciplineChart = Add-Chart $dashboard $disciplineSource "Confirmed Destination Rates by Discipline" 51 780 435 690 250 $true -CategoryAxisTitle "Discipline" -ValueAxisTitle "Confirmed destinations in tier (%)"
    Set-ChartSeries $disciplineChart $dashboard.Range("X19:X20") @(
        [pscustomobject]@{ Name = "T10"; Values = $dashboard.Range("Y19:Y20") },
        [pscustomobject]@{ Name = "T25"; Values = $dashboard.Range("Z19:Z20") },
        [pscustomobject]@{ Name = "T50"; Values = $dashboard.Range("AA19:AA20") },
        [pscustomobject]@{ Name = "T100"; Values = $dashboard.Range("AB19:AB20") }
    )
    $disciplineChart.Axes(2).TickLabels.NumberFormat = "0%"
    $binChart = Add-Chart $dashboard $dashboard.Range("A24:B32") "Destination Bins and Unresolved Records" 57 780 700 520 285 $false -CategoryAxisTitle "Destination or resolution bin" -ValueAxisTitle "Unique champions (count)"
    Set-ChartSeries $binChart $dashboard.Range("A25:A32") @(
        [pscustomobject]@{ Name = "Unique champions"; Values = $dashboard.Range("B25:B32") }
    )
    if ($topEnd -ge 25) {
        $topChart = Add-Chart $dashboard $dashboard.Range("D24:E$topEnd") "Most Frequent Confirmed Destinations (Ties Included)" 57 20 805 350 320 $false -CategoryAxisTitle "College" -ValueAxisTitle "Confirmed unique champions (count)"
        Set-ChartSeries $topChart $dashboard.Range("D25:D$topEnd") @(
            [pscustomobject]@{ Name = "Unique champions"; Values = $dashboard.Range("E25:E$topEnd") }
        )
    }
    $coverageChart = Add-Chart $dashboard $dashboard.Range("G24:H28") "Public Match Coverage" 5 20 500 330 285 $true
    Set-ChartSeries $coverageChart $dashboard.Range("G25:G28") @(
        [pscustomobject]@{ Name = "Unique champions"; Values = $dashboard.Range("H25:H28") }
    )
    $dashboard.Columns("X:AB").Hidden = $true

    $dashboard.Columns("A").ColumnWidth = 24
    $dashboard.Columns("B").ColumnWidth = 16
    $dashboard.Columns("C:E").ColumnWidth = 22
    $dashboard.Columns("F").ColumnWidth = 13
    $dashboard.Columns("G:H").ColumnWidth = 19
    $dashboard.Columns("I").ColumnWidth = 3
    $dashboard.Columns("J:K").ColumnWidth = 18
    $dashboard.Columns("L:O").ColumnWidth = 12
    $dashboard.Columns("P:V").ColumnWidth = 10
    $dashboard.Range("A1:Q40").Font.Name = "Aptos"

    $tierSheet = $workbook.Worksheets.Item("Tier Analysis")
    Set-Title $tierSheet "A1:H1" "Tier Analysis and Sensitivity Checks"
    $tierSheet.Range("A3:H3").Merge()
    $tierSheet.Range("A3").Value2 = "Nested tiers use current Forbes ranks. Confirmed-only is primary; confirmed + probable is a sensitivity case."
    $null = Write-Row $tierSheet 5 1 @("Tier", "Primary count", "Primary known rate", "Primary all-cohort rate", "Sensitivity count", "Sensitivity known rate", "Nonconfirmed upper bound", "Interpretation")
    Set-SectionHeader $tierSheet.Range("A5:H5")
    for ($i = 0; $i -lt $tierRows.Count; $i++) {
        $rowNumber = 6 + $i
        $flagColumn = $tierFlags[$i]
        $tierSheet.Cells.Item($rowNumber, 1).Value2 = $tierRows[$i]
        $tierSheet.Cells.Item($rowNumber, 2).FormulaR1C1 = "=SUMIFS('Unique Champions'!R4C${flagColumn}:R${uniqueEnd}C${flagColumn},'Unique Champions'!R4C25:R${uniqueEnd}C25,1)"
        $tierSheet.Cells.Item($rowNumber, 3).FormulaR1C1 = "=RC[-1]/SUM('Unique Champions'!R4C25:R${uniqueEnd}C25)"
        $tierSheet.Cells.Item($rowNumber, 4).FormulaR1C1 = "=RC[-2]/COUNTA('Unique Champions'!R4C1:R${uniqueEnd}C1)"
        $tierSheet.Cells.Item($rowNumber, 5).FormulaR1C1 = "=SUMIFS('Unique Champions'!R4C${flagColumn}:R${uniqueEnd}C${flagColumn},'Unique Champions'!R4C26:R${uniqueEnd}C26,1)"
        $tierSheet.Cells.Item($rowNumber, 6).FormulaR1C1 = "=RC[-1]/SUM('Unique Champions'!R4C26:R${uniqueEnd}C26)"
        $tierSheet.Cells.Item($rowNumber, 7).FormulaR1C1 = "=(RC[-5]+(COUNTA('Unique Champions'!R4C1:R${uniqueEnd}C1)-SUM('Unique Champions'!R4C25:R${uniqueEnd}C25)))/COUNTA('Unique Champions'!R4C1:R${uniqueEnd}C1)"
        $tierSheet.Cells.Item($rowNumber, 8).Value2 = if ($tierRows[$i] -eq "MIT") { "MIT-specific count; MIT is also rank 1 in this ranking." } else { "Cumulative: includes every institution ranked at or above this cutoff." }
    }
    $tierSheet.Range("C6:D11").NumberFormat = "0.0%"
    $tierSheet.Range("F6:G11").NumberFormat = "0.0%"
    $tierSheet.Range("A5:H11").Borders.LineStyle = 1
    $tierSheet.Range("A12:H12").Merge()
    $tierSheet.Range("A12").Value2 = "MIT and T1 are the same cutoff in this edition because MIT is Forbes rank 1."
    $tierSheet.Range("A12").Font.Italic = $true
    $tierSheet.Range("A12").Font.Color = 0x735B45
    $tierSheet.Range("A14:H14").Merge()
    $tierSheet.Range("A14").Value2 = "Denominator guide"
    Set-SectionHeader $tierSheet.Range("A14:H14")
    $tierNotes = @(
        @("Primary known rate", "Confirmed tier count / all confirmed destinations. Most intuitive, but vulnerable to non-random missingness."),
        @("Primary all-cohort rate", "Confirmed tier count / every unique champion. Conservative lower bound."),
        @("Sensitivity known rate", "Confirmed + probable tier count / confirmed + probable destinations."),
        @("Nonconfirmed upper bound", "Assumes every record not confirmed lies in the tier. This is a logical ceiling, not an estimate.")
    )
    $tierNoteRange = Write-Matrix $tierSheet 15 1 $tierNotes
    $tierNoteRange.WrapText = $true

    $eventAnalysisHeaders = @("Event", "Unique n", "Coverage", "T10", "T25", "T50", "T100")
    $null = Write-Row $tierSheet 21 1 $eventAnalysisHeaders
    Set-SectionHeader $tierSheet.Range("A21:G21")
    $analysisEvents = @(
        "Lincoln-Douglas Debate",
        "Policy Debate",
        "Public Forum Debate",
        "International Extemporaneous Speaking",
        "United States Extemporaneous Speaking",
        "Original Oratory",
        "Duo Interpretation"
    )
    for ($i = 0; $i -lt $analysisEvents.Count; $i++) {
        $rowNumber = 22 + $i
        $eventLabel = $analysisEvents[$i]
        $tierSheet.Cells.Item($rowNumber, 1).Value2 = $eventLabel
        $tierSheet.Cells.Item($rowNumber, 2).FormulaR1C1 = "=COUNTIF('Unique Champions'!R4C9:R${uniqueEnd}C9,`"*$eventLabel*`")"
        $tierSheet.Cells.Item($rowNumber, 3).FormulaR1C1 = "=COUNTIFS('Unique Champions'!R4C9:R${uniqueEnd}C9,`"*$eventLabel*`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)/RC[-1]"
        $tierSheet.Cells.Item($rowNumber, 4).FormulaR1C1 = "=SUMIFS('Unique Champions'!R4C21:R${uniqueEnd}C21,'Unique Champions'!R4C9:R${uniqueEnd}C9,`"*$eventLabel*`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)/COUNTIFS('Unique Champions'!R4C9:R${uniqueEnd}C9,`"*$eventLabel*`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)"
        $tierSheet.Cells.Item($rowNumber, 5).FormulaR1C1 = "=SUMIFS('Unique Champions'!R4C22:R${uniqueEnd}C22,'Unique Champions'!R4C9:R${uniqueEnd}C9,`"*$eventLabel*`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)/COUNTIFS('Unique Champions'!R4C9:R${uniqueEnd}C9,`"*$eventLabel*`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)"
        $tierSheet.Cells.Item($rowNumber, 6).FormulaR1C1 = "=SUMIFS('Unique Champions'!R4C23:R${uniqueEnd}C23,'Unique Champions'!R4C9:R${uniqueEnd}C9,`"*$eventLabel*`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)/COUNTIFS('Unique Champions'!R4C9:R${uniqueEnd}C9,`"*$eventLabel*`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)"
        $tierSheet.Cells.Item($rowNumber, 7).FormulaR1C1 = "=SUMIFS('Unique Champions'!R4C24:R${uniqueEnd}C24,'Unique Champions'!R4C9:R${uniqueEnd}C9,`"*$eventLabel*`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)/COUNTIFS('Unique Champions'!R4C9:R${uniqueEnd}C9,`"*$eventLabel*`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)"
    }
    $tierSheet.Range("C22:G28").NumberFormat = "0.0%"
    $tierSheet.Range("A21:G28").Borders.LineStyle = 1

    $periodHeaders = @("First championship period", "Unique n", "Coverage", "T10", "T25", "T50", "T100")
    $null = Write-Row $tierSheet 31 1 $periodHeaders
    Set-SectionHeader $tierSheet.Range("A31:G31")
    $periods = @(
        @("2007-2011", 2007, 2011),
        @("2012-2016", 2012, 2016),
        @("2017-2021", 2017, 2021)
    )
    for ($i = 0; $i -lt $periods.Count; $i++) {
        $rowNumber = 32 + $i
        $label = $periods[$i][0]
        $startYear = $periods[$i][1]
        $endYear = $periods[$i][2]
        $tierSheet.Cells.Item($rowNumber, 1).Value2 = $label
        $tierSheet.Cells.Item($rowNumber, 2).FormulaR1C1 = "=COUNTIFS('Unique Champions'!R4C5:R${uniqueEnd}C5,`">=$startYear`",'Unique Champions'!R4C5:R${uniqueEnd}C5,`"<=$endYear`")"
        $tierSheet.Cells.Item($rowNumber, 3).FormulaR1C1 = "=COUNTIFS('Unique Champions'!R4C5:R${uniqueEnd}C5,`">=$startYear`",'Unique Champions'!R4C5:R${uniqueEnd}C5,`"<=$endYear`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)/RC[-1]"
        $tierSheet.Cells.Item($rowNumber, 4).FormulaR1C1 = "=SUMIFS('Unique Champions'!R4C21:R${uniqueEnd}C21,'Unique Champions'!R4C5:R${uniqueEnd}C5,`">=$startYear`",'Unique Champions'!R4C5:R${uniqueEnd}C5,`"<=$endYear`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)/COUNTIFS('Unique Champions'!R4C5:R${uniqueEnd}C5,`">=$startYear`",'Unique Champions'!R4C5:R${uniqueEnd}C5,`"<=$endYear`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)"
        $tierSheet.Cells.Item($rowNumber, 5).FormulaR1C1 = "=SUMIFS('Unique Champions'!R4C22:R${uniqueEnd}C22,'Unique Champions'!R4C5:R${uniqueEnd}C5,`">=$startYear`",'Unique Champions'!R4C5:R${uniqueEnd}C5,`"<=$endYear`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)/COUNTIFS('Unique Champions'!R4C5:R${uniqueEnd}C5,`">=$startYear`",'Unique Champions'!R4C5:R${uniqueEnd}C5,`"<=$endYear`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)"
        $tierSheet.Cells.Item($rowNumber, 6).FormulaR1C1 = "=SUMIFS('Unique Champions'!R4C23:R${uniqueEnd}C23,'Unique Champions'!R4C5:R${uniqueEnd}C5,`">=$startYear`",'Unique Champions'!R4C5:R${uniqueEnd}C5,`"<=$endYear`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)/COUNTIFS('Unique Champions'!R4C5:R${uniqueEnd}C5,`">=$startYear`",'Unique Champions'!R4C5:R${uniqueEnd}C5,`"<=$endYear`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)"
        $tierSheet.Cells.Item($rowNumber, 7).FormulaR1C1 = "=SUMIFS('Unique Champions'!R4C24:R${uniqueEnd}C24,'Unique Champions'!R4C5:R${uniqueEnd}C5,`">=$startYear`",'Unique Champions'!R4C5:R${uniqueEnd}C5,`"<=$endYear`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)/COUNTIFS('Unique Champions'!R4C5:R${uniqueEnd}C5,`">=$startYear`",'Unique Champions'!R4C5:R${uniqueEnd}C5,`"<=$endYear`",'Unique Champions'!R4C25:R${uniqueEnd}C25,1)"
    }
    $tierSheet.Range("C32:G34").NumberFormat = "0.0%"
    $tierSheet.Range("A31:G34").Borders.LineStyle = 1

    $null = Write-Row $tierSheet 21 10 @("Event", "T10", "T25", "T50", "T100")
    for ($r = 22; $r -le 28; $r++) {
        $tierSheet.Cells.Item($r, 10).Formula = "=A$r"
        $tierSheet.Cells.Item($r, 11).Formula = "=D$r"
        $tierSheet.Cells.Item($r, 12).Formula = "=E$r"
        $tierSheet.Cells.Item($r, 13).Formula = "=F$r"
        $tierSheet.Cells.Item($r, 14).Formula = "=G$r"
    }
    $eventChartSource = $tierSheet.Range("J21:N28")
    $eventChart = Add-Chart $tierSheet $eventChartSource "Confirmed Selective-College Rates by Event" 57 720 350 680 330 $true -CategoryAxisTitle "Event" -ValueAxisTitle "Confirmed destinations in tier (%)"
    Set-ChartSeries $eventChart $tierSheet.Range("J22:J28") @(
        [pscustomobject]@{ Name = "T10"; Values = $tierSheet.Range("K22:K28") },
        [pscustomobject]@{ Name = "T25"; Values = $tierSheet.Range("L22:L28") },
        [pscustomobject]@{ Name = "T50"; Values = $tierSheet.Range("M22:M28") },
        [pscustomobject]@{ Name = "T100"; Values = $tierSheet.Range("N22:N28") }
    )
    $eventChart.Axes(2).TickLabels.NumberFormat = "0%"
    $null = Write-Row $tierSheet 31 10 @("Period", "T10", "T25", "T50", "T100")
    for ($r = 32; $r -le 34; $r++) {
        $tierSheet.Cells.Item($r, 10).Formula = "=A$r"
        $tierSheet.Cells.Item($r, 11).Formula = "=D$r"
        $tierSheet.Cells.Item($r, 12).Formula = "=E$r"
        $tierSheet.Cells.Item($r, 13).Formula = "=F$r"
        $tierSheet.Cells.Item($r, 14).Formula = "=G$r"
    }
    $periodChartSource = $tierSheet.Range("J31:N34")
    $periodChart = Add-Chart $tierSheet $periodChartSource "Rates by First Championship Period" 51 720 700 680 280 $true -CategoryAxisTitle "First championship period" -ValueAxisTitle "Confirmed destinations in tier (%)"
    Set-ChartSeries $periodChart $tierSheet.Range("J32:J34") @(
        [pscustomobject]@{ Name = "T10"; Values = $tierSheet.Range("K32:K34") },
        [pscustomobject]@{ Name = "T25"; Values = $tierSheet.Range("L32:L34") },
        [pscustomobject]@{ Name = "T50"; Values = $tierSheet.Range("M32:M34") },
        [pscustomobject]@{ Name = "T100"; Values = $tierSheet.Range("N32:N34") }
    )
    $periodChart.Axes(2).TickLabels.NumberFormat = "0%"
    $tierSheet.Columns("J:N").Hidden = $true

    $tierSheet.Columns("A").ColumnWidth = 24
    $tierSheet.Columns("B:G").ColumnWidth = 20
    $tierSheet.Columns("H").ColumnWidth = 60
    $tierSheet.Range("A1:H40").Font.Name = "Aptos"

    $collegeSheet = $workbook.Worksheets.Item("College Destinations")
    Set-Title $collegeSheet "A1:F1" "Observed College Destinations"
    $collegeHeaders = @("college_canonical", "confirmed_unique_champions", "probable_unique_champions", "forbes_rank", "rank_bin", "note")
    $collegeMatrix = New-Object System.Collections.ArrayList
    $null = $collegeMatrix.Add([object[]]$collegeHeaders)
    $collegeGroups = @(
        $uniqueRows |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_.college_canonical) } |
            Group-Object college_canonical |
            Sort-Object Name
    )
    foreach ($group in $collegeGroups) {
        $confirmedCount = @($group.Group | Where-Object { $_.college_match_status -eq "confirmed" }).Count
        $probableCount = @($group.Group | Where-Object { $_.college_match_status -eq "probable" }).Count
        $null = $collegeMatrix.Add([object[]]@(
            $group.Name, $confirmedCount, $probableCount, "", "",
            "Counts are unique people, not participant-event rows."
        ))
    }
    $collegeRange = Write-Matrix $collegeSheet 3 1 $collegeMatrix
    $collegeEnd = 3 + $collegeGroups.Count
    for ($r = 4; $r -le $collegeEnd; $r++) {
        $collegeSheet.Cells.Item($r, 4).Formula = "=IFERROR(INDEX(Rankings!`$B`$4:`$B`$103,MATCH(A$r,Rankings!`$A`$4:`$A`$103,0)),`"`")"
        $collegeSheet.Cells.Item($r, 5).Formula = "=IF(OR(A$r=`"University of Oxford`",A$r=`"McGill University`",A$r=`"University of Cambridge`",A$r=`"London School of Economics and Political Science`"),`"Non-U.S.`",IF(D$r=`"`",`"U.S. >100 / unranked`",IF(D$r=1,`"Rank 1`",IF(D$r<=10,`"Ranks 2-10`",IF(D$r<=25,`"Ranks 11-25`",IF(D$r<=50,`"Ranks 26-50`",`"Ranks 51-100`"))))))"
    }
    $null = Add-ExcelTable $collegeSheet $collegeRange "CollegeDestinationsTable"
    $collegeSheet.Columns("A").ColumnWidth = 38
    $collegeSheet.Columns("B:C").ColumnWidth = 25
    $collegeSheet.Columns("D:E").ColumnWidth = 18
    $collegeSheet.Columns("F").ColumnWidth = 50
    $collegeSheet.Range("A3:F$collegeEnd").WrapText = $true

    $evidenceSheet = $workbook.Worksheets.Item("Published Evidence")
    Set-Title $evidenceSheet "A1:U1" "Published Aggregate Evidence"
    $evidenceSheet.Range("A2:U2").Merge()
    $evidenceSheet.Range("A2").Value2 = "Different samples and designs are shown separately. Do not pool these rows into a single causal estimate."
    $evidenceHeaders = @(
        "evidence_id", "study_or_dataset", "year", "population", "exposure_or_sample", "outcome",
        "debate_value", "comparison_value", "unit", "absolute_difference", "relative_ratio",
        "sample_size_debate", "sample_size_total", "source_url", "source_type", "design", "authors",
        "publication", "quality_tier", "key_limitations", "notes"
    )
    $evidenceMatrix = New-Object System.Collections.ArrayList
    $null = $evidenceMatrix.Add([object[]]$evidenceHeaders)
    foreach ($row in $aggregateRows) {
        $values = New-Object System.Collections.ArrayList
        foreach ($header in $evidenceHeaders) {
            $value = Get-TextValue $row $header
            if ($header -in @("year", "debate_value", "comparison_value", "absolute_difference", "relative_ratio", "sample_size_debate", "sample_size_total")) {
                $numeric = 0.0
                if ([double]::TryParse($value, [ref]$numeric)) {
                    $value = $numeric
                }
            }
            $null = $values.Add($value)
        }
        $null = $evidenceMatrix.Add([object[]]$values.ToArray())
    }
    $evidenceRange = Write-Matrix $evidenceSheet 20 1 $evidenceMatrix
    $evidenceEnd = 20 + $aggregateRows.Count
    $null = Add-ExcelTable $evidenceSheet $evidenceRange "PublishedEvidenceTable" "TableStyleMedium4"
    $evidenceById = @{}
    foreach ($row in $aggregateRows) {
        $evidenceById[(Get-TextValue $row "evidence_id")] = $row
    }
    $nsdaChartRows = New-Object System.Collections.ArrayList
    $null = $nsdaChartRows.Add([object[]]@("Reported tier", "NSDA survey respondents", "Reported national benchmark"))
    foreach ($id in @("NSDA2019_TOP10", "NSDA2019_TOP25", "NSDA2019_TOP50")) {
        if ($evidenceById.ContainsKey($id)) {
            $row = $evidenceById[$id]
            $label = (Get-TextValue $row "outcome") -replace "Enrollment at a ", ""
            $null = $nsdaChartRows.Add([object[]]@(
                $label,
                [double](Get-TextValue $row "debate_value"),
                [double](Get-TextValue $row "comparison_value")
            ))
        }
    }
    $nsdaChartRange = Write-Matrix $evidenceSheet 5 1 $nsdaChartRows
    Set-SectionHeader $evidenceSheet.Range("A5:C5")
    $nsdaChart = Add-Chart $evidenceSheet $nsdaChartRange "NSDA Class-of-2019 Survey: Reported Top-College Enrollment" 51 420 70 570 275 $true -CategoryAxisTitle "Reported ranking cutoff" -ValueAxisTitle "Enrollment (%)"
    Set-ChartSeries $nsdaChart $evidenceSheet.Range("A6:A8") @(
        [pscustomobject]@{ Name = "NSDA survey respondents"; Values = $evidenceSheet.Range("B6:B8") },
        [pscustomobject]@{ Name = "Reported national benchmark"; Values = $evidenceSheet.Range("C6:C8") }
    )
    $nsdaChart.Axes(2).TickLabels.NumberFormat = '0\%'

    $bostonChartRows = New-Object System.Collections.ArrayList
    $null = $bostonChartRows.Add([object[]]@("Outcome", "Debate participants", "Adjusted comparison"))
    foreach ($id in @("BDL_GRAD5", "BDL_POSTSEC2")) {
        if ($evidenceById.ContainsKey($id)) {
            $row = $evidenceById[$id]
            $label = if ($id -eq "BDL_GRAD5") { "Graduated within 5 years" } else { "Postsecondary enrollment within 2 years" }
            $null = $bostonChartRows.Add([object[]]@(
                $label,
                [double](Get-TextValue $row "debate_value"),
                [double](Get-TextValue $row "comparison_value")
            ))
        }
    }
    $bostonChartRange = Write-Matrix $evidenceSheet 5 11 $bostonChartRows
    Set-SectionHeader $evidenceSheet.Range("K5:M5")
    $bostonChart = Add-Chart $evidenceSheet $bostonChartRange "Boston Debate League: Adjusted Outcome Rates" 51 1190 70 570 275 $true -CategoryAxisTitle "Outcome" -ValueAxisTitle "Students (%)"
    Set-ChartSeries $bostonChart $evidenceSheet.Range("K6:K7") @(
        [pscustomobject]@{ Name = "Debate participants"; Values = $evidenceSheet.Range("L6:L7") },
        [pscustomobject]@{ Name = "Adjusted comparison"; Values = $evidenceSheet.Range("M6:M7") }
    )
    $bostonChart.Axes(2).TickLabels.NumberFormat = '0\%'

    $evidenceSheet.Range("A13:U13").Merge()
    $evidenceSheet.Range("A13").Value2 = "Design warning"
    Set-SectionHeader $evidenceSheet.Range("A13:U13")
    $evidenceSheet.Range("A14:U16").Merge()
    $evidenceSheet.Range("A14").Value2 = "The NSDA chart is a self-reported respondent-versus-benchmark comparison with undisclosed ranking and benchmark methods. The Boston rates are adjusted observational estimates; the fixed-effects design applies to repeated ELA outcomes, not these one-time graduation and enrollment outcomes. Neither chart establishes that debate caused the difference."
    $evidenceSheet.Range("A14").WrapText = $true
    $evidenceSheet.Range("A14").VerticalAlignment = -4160
    $evidenceSheet.Columns("A").ColumnWidth = 18
    $evidenceSheet.Columns("B:F").ColumnWidth = 28
    $evidenceSheet.Columns("G:M").ColumnWidth = 18
    $evidenceSheet.Columns("N").ColumnWidth = 55
    $evidenceSheet.Columns("O:S").ColumnWidth = 22
    $evidenceSheet.Columns("T:U").ColumnWidth = 55
    $evidenceSheet.Range("A5:U$evidenceEnd").WrapText = $true

    $auditSheet = $workbook.Worksheets.Item("Source Audit")
    Set-Title $auditSheet "A1:L1" "Participant Match and Source Audit"
    $auditHeaders = @(
        "person_id", "participant_name", "high_school", "years", "events", "college", "match_status",
        "confidence", "result_source_url", "college_source_url", "source_type", "identity_evidence"
    )
    $auditMatrix = New-Object System.Collections.ArrayList
    $null = $auditMatrix.Add([object[]]$auditHeaders)
    foreach ($row in $uniqueRows) {
        $yearLabel = if ($row.first_year -eq $row.last_year) { "$($row.first_year)" } else { "$($row.first_year)-$($row.last_year)" }
        $null = $auditMatrix.Add([object[]]@(
            $row.person_id, $row.participant_name, $row.high_school,
            $yearLabel,
            $row.events, $row.college, $row.college_match_status, $row.college_match_confidence,
            $row.result_source_url, $row.college_source_url, $row.college_source_type, $row.match_notes
        ))
    }
    $auditRange = Write-Matrix $auditSheet 3 1 $auditMatrix
    $auditEnd = 3 + $uniqueRows.Count
    $null = Add-ExcelTable $auditSheet $auditRange "SourceAuditTable" "TableStyleMedium9"
    $auditSheet.Columns("A").ColumnWidth = 10
    $auditSheet.Columns("B:C").ColumnWidth = 25
    $auditSheet.Columns("D").ColumnWidth = 14
    $auditSheet.Columns("E:F").ColumnWidth = 32
    $auditSheet.Columns("G:H").ColumnWidth = 16
    $auditSheet.Columns("I:J").ColumnWidth = 55
    $auditSheet.Columns("K").ColumnWidth = 24
    $auditSheet.Columns("L").ColumnWidth = 75
    $auditSheet.Range("A3:L$auditEnd").WrapText = $true
    for ($r = 4; $r -le $auditEnd; $r++) {
        $resultUrl = [string]$auditSheet.Cells.Item($r, 9).Value2
        $collegeUrl = [string]$auditSheet.Cells.Item($r, 10).Value2
        if (-not [string]::IsNullOrWhiteSpace($resultUrl)) {
            Add-Link $auditSheet $auditSheet.Cells.Item($r, 9) $resultUrl "Tournament source"
        }
        if (-not [string]::IsNullOrWhiteSpace($collegeUrl)) {
            Add-Link $auditSheet $auditSheet.Cells.Item($r, 10) $collegeUrl "College evidence"
        }
    }

    $methodsSheet = $workbook.Worksheets.Item("Methods")
    Set-Title $methodsSheet "A1:H1" "Study Protocol and Interpretation Limits"
    $protocolLines = @(Get-Content -LiteralPath $protocolFile -Encoding UTF8)
    $methodRow = 3
    foreach ($line in $protocolLines) {
        if ($line -match "^# (.+)$") {
            continue
        }
        if ($line -match "^## (.+)$") {
            $methodsSheet.Range("A$methodRow:H$methodRow").Merge()
            $methodsSheet.Cells.Item($methodRow, 1).Value2 = $Matches[1]
            Set-SectionHeader $methodsSheet.Range("A$methodRow:H$methodRow")
            $methodRow++
            continue
        }
        if ([string]::IsNullOrWhiteSpace($line)) {
            $methodRow++
            continue
        }
        $methodsSheet.Range("A$methodRow:H$methodRow").Merge()
        $methodsSheet.Cells.Item($methodRow, 1).Value2 = ($line -replace "^- ", "- ")
        $methodsSheet.Cells.Item($methodRow, 1).WrapText = $true
        $methodsSheet.Cells.Item($methodRow, 1).VerticalAlignment = -4160
        $methodRow++
    }
    $methodsSheet.Columns("A:H").ColumnWidth = 15
    $methodsSheet.Range("A1:H$methodRow").Font.Name = "Aptos"

    foreach ($sheet in @($uniqueSheet, $recordsSheet, $rankings, $evidenceSheet, $auditSheet, $collegeSheet)) {
        $sheet.Activate()
        $sheet.Range("A4").Select()
        $excel.ActiveWindow.FreezePanes = $false
        $excel.ActiveWindow.FreezePanes = $true
        $sheet.Range("A1").Select()
    }
    foreach ($sheet in @($readMe, $dashboard, $tierSheet, $methodsSheet)) {
        $sheet.Activate()
        $sheet.Range("A1").Select()
    }

    $dashboard.Activate()
    $dashboard.Range("A1").Select()
    $excel.ActiveWindow.Zoom = 85
    $dashboard.PageSetup.Orientation = 2
    $dashboard.PageSetup.Zoom = $false
    $dashboard.PageSetup.FitToPagesWide = 1
    $dashboard.PageSetup.FitToPagesTall = 1
    $dashboard.PageSetup.PrintArea = "`$A`$1:`$Q`$80"

    foreach ($sheet in $workbook.Worksheets) {
        $sheet.Activate()
        $usedRange = $sheet.UsedRange
        $usedRange.Font.Name = "Aptos"
        $usedRange.Rows.AutoFit()
        foreach ($chartObject in $sheet.ChartObjects()) {
            $chartObject.Placement = 3
        }
        $sheet.Range("A1").Select()
    }
    $eventChart.Parent.Width = 680
    $eventChart.Parent.Height = 330
    $periodChart.Parent.Width = 680
    $periodChart.Parent.Height = 280

    if (Test-Path -LiteralPath $Output) {
        Remove-Item -LiteralPath $Output -Force
    }
    if (Test-Path -LiteralPath $pdfOutput) {
        Remove-Item -LiteralPath $pdfOutput -Force
    }
    foreach ($sheet in $workbook.Worksheets) {
        foreach ($chartObject in $sheet.ChartObjects()) {
            $chartObject.Chart.Refresh()
        }
    }
    $excel.ScreenUpdating = $true
    $excel.CalculateFullRebuild()
    $workbook.SaveAs($Output, 51)
    $workbook.Close($true)
    $workbook = $null

    $checkWorkbook = $excel.Workbooks.Open($Output, 0, $true)
    $checkDashboard = $checkWorkbook.Worksheets.Item("Dashboard")
    $checkDashboard.Activate()
    foreach ($chartObject in $checkDashboard.ChartObjects()) {
        $chartObject.Chart.Refresh()
    }
    $checkDashboard.ExportAsFixedFormat(0, $pdfOutput)
    $sheetCount = $checkWorkbook.Worksheets.Count
    $chartCount = 0
    foreach ($sheet in $checkWorkbook.Worksheets) {
        $chartCount += $sheet.ChartObjects().Count
    }
    $checkUniqueCount = $checkWorkbook.Worksheets.Item("Dashboard").Range("A5").Value2
    $checkConfirmedCount = $checkWorkbook.Worksheets.Item("Dashboard").Range("D5").Value2
    $checkWorkbook.Close($false)

    if ($sheetCount -ne 10) {
        throw "Workbook verification failed: expected 10 sheets, found $sheetCount."
    }
    if ($chartCount -lt 5) {
        throw "Workbook verification failed: expected at least 5 charts, found $chartCount."
    }
    if ([int]$checkUniqueCount -ne $uniqueRows.Count) {
        throw "Workbook verification failed: dashboard unique count $checkUniqueCount does not match $($uniqueRows.Count)."
    }

    Write-Output "Workbook: $Output"
    Write-Output "Dashboard PDF: $pdfOutput"
    Write-Output "Champion performance rows: $($allRows.Count)"
    Write-Output "Unique champions: $($uniqueRows.Count)"
    Write-Output "Confirmed destinations: $checkConfirmedCount"
    Write-Output "Published evidence rows: $($aggregateRows.Count)"
    Write-Output "Charts: $chartCount"
}
finally {
    if ($null -ne $workbook) {
        try { $workbook.Close($false) } catch {}
    }
    if ($null -ne $excel) {
        try { $excel.Quit() } catch {}
        try { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel) } catch {}
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
