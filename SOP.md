# Comet Clips Review SOP

## Check That Supabase Is Updating

Use this after a reviewer clicks `Submit rating` in the Streamlit app.

1. Open Supabase.
2. Go to `Table Editor`.
3. Open the `ratings` table.
4. Sort by `submitted_at` descending, or run this in SQL Editor:

```sql
select
  reviewer_email,
  content_id,
  clip_type,
  clip_id,
  clip_set_key,
  unique_clip_key,
  score,
  submitted_at
from ratings
order by submitted_at desc
limit 20;
```

5. Confirm the latest row has the expected reviewer email and score.
6. Confirm the row is attached to the right clip:

```text
content_id::prompt::model::clip_id
```

Example:

```text
1260029222::momenttype::pro::clip1
```

## Check The Rating Is Against The Right Clip

Match the app screen to Supabase using these fields:

- `content_id`
- `clip_type`
- `clip_id`
- `unique_clip_key`

Output set mapping:

| App label | Prompt | Model | clip_type |
| --- | --- | --- | --- |
| Alpha | Cliffhanger | Pro | `cliffhanger_pro` |
| Beta | Cliffhanger | Flash | `cliffhanger_flash` |
| Gamma | Moment Type | Pro | `momenttype_pro` |
| Delta | Moment Type | Flash | `momenttype_flash` |

For example, if the app shows content `1260029222`, output set `Gamma`, and
clip `clip1`, the Supabase row should have:

```text
content_id = 1260029222
clip_type = momenttype_pro
clip_id = clip1
unique_clip_key = 1260029222::momenttype::pro::clip1
```

## Check Average User Ratings

Run this query in Supabase SQL Editor:

```sql
select
  unique_clip_key,
  avg(score)::numeric(10,2) as avg_user_rating,
  count(*) as rating_count
from ratings
where unique_clip_key is not null
group by unique_clip_key
order by unique_clip_key;
```

If a rating was saved through the fallback path and `unique_clip_key` is blank,
run this repair query:

```sql
update ratings
set
  clip_set_key = public.comet_clip_set_key(content_id, clip_type),
  unique_clip_key = public.comet_clip_set_key(content_id, clip_type) || '::' || clip_id
where unique_clip_key is null
  and content_id is not null
  and clip_type is not null
  and clip_id is not null;
```

Then rerun the average query.

## Copy Average User Ratings To The Sheet With Clip Drive Links

There are two supported methods.

### Method 1: Download From The App

1. Open the Streamlit app.
2. Sign in as an admin.
3. Open `Admin view`.
4. Click `Download Excel with average ratings`.
5. The downloaded workbook includes:
   - `content_id`
   - `content_name`
   - `output_set`
   - `clip_id`
   - `unique_clip_key`
   - `clip_drive_link`
   - `Genre CMS`
   - `description`
   - `Avg User Rating`
   - `Rating Count`

Use this when you want a fresh workbook generated from the app data.

### Method 2: Update The Original Workbook

Use this when you want to keep your original workbook layout and add ratings to
the existing tabs.

From the repo folder, run:

```bash
python update_excel_with_ratings.py /path/to/original.xlsx /path/to/original_with_ratings.xlsx
```

Example:

```bash
python update_excel_with_ratings.py "/Users/anushreepande/Downloads/comet_clips.xlsx" "/Users/anushreepande/Downloads/comet_clips_with_ratings.xlsx"
```

The script looks for tabs with `content_id` and `clip_id`, infers the output set
from the tab name or `output_set` / `output_label`, then adds or updates:

- `Unique Clip Key`
- `Avg User Rating`
- `Rating Count`

It preserves the original file unless you intentionally use the same path for
input and output.

## Manual Copy Into A Sheet

If you prefer to copy from Supabase manually:

1. Run the average query above.
2. Export the result as CSV.
3. In your sheet, create a helper column called `Unique Clip Key`.
4. Build it as:

```text
content_id::prompt::model::clip_id
```

5. Use lookup logic in Excel or Google Sheets to bring in `avg_user_rating` and
`rating_count` from the exported CSV.
6. Keep `clip_drive_link` in the original sheet as the clip reference.

The important rule is that averages must be matched using `unique_clip_key`, not
only `clip_id`, because `clip1`, `clip2`, etc. repeat across content and output
sets.
