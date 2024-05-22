import streamlit as st
import datetime as dt
import pandas as pd
import numpy as np
import io
import re


st.sidebar.title(":violet[Luminator]")

# Create a file uploader
with st.sidebar.popover(
    "Upload Files", help="Upload your streaming report files", use_container_width=True
):
    uploaded_files = st.file_uploader(
        "Upload your streaming report files",
        accept_multiple_files=True,
        type=["csv"],
    )


def process_file(file):
    # Determine the file type and read data accordingly
    if file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        df = pd.DataFrame(
            pd.read_excel(io=file, skiprows=6)  # Assuming header starts at row 7
        )
    else:
        df = pd.read_csv(
            io.BytesIO(file.read()), skiprows=6
        )  # Assuming header starts at row 7

    # Collect datetime of latest date in rolling date range column
    latest_date = df["Range"][0]

    # Rename columns and clean data
    column_rename = {
        "Range": "Rolling Date Range",
        "TP.7": "This Period Streams",
        "TP.8": "Audio Streams This Period",
        "TP.9": "Video Streams This Period",
        "% Chg.7": "This Period Streams % Change",
        "% Chg.8": "Audio Streams This Period % Change",
        "% Chg.9": "Video Streams This Period % Change",
        "YTD (" + latest_date + ").7": "YTD Streams",
        "YTD (" + latest_date + ").8": "YTD Audio Streams",
        "YTD (" + latest_date + ").9": "YTD Video Streams",
        "ATD (" + latest_date + ").7": "ATD Streams",
        "ATD (" + latest_date + ").8": "ATD Audio Streams",
        "ATD (" + latest_date + ").9": "ATD Video Streams",
        # Add additional column mappings if necessary
    }
    # Drop the 4th column
    df.drop(columns=df.columns[1], inplace=True)
    df.drop(columns=df.columns[3:31], inplace=True)
    df.drop(columns=df.columns[15:], inplace=True)

    df.rename(columns=column_rename, inplace=True)
    df.drop(columns=[col for col in df.columns if "Unnamed" in col], inplace=True)
    df = df.apply(
        lambda x: x.str.strip() if x.dtype == "object" else x
    )  # Strip whitespace from strings
    df = df.apply(
        lambda x: x.str.replace(",", "") if x.dtype == "object" else x
    )  # Remove commas from strings
    return df


# Process each uploaded file
all_data = []
for uploaded_file in uploaded_files:
    if uploaded_file is not None:
        df = process_file(uploaded_file)
        all_data.append(df)

# Aggregate data
if all_data:
    aggregated_data = pd.concat(all_data)

    aggregated_data["Rolling Date Range"] = pd.to_datetime(
        aggregated_data["Rolling Date Range"]
    )

    # Initialize an empty DataFrame for the result
    result_df = pd.DataFrame(columns=["Artist"])

    # Group by artist and aggregate data
    for artist, group in aggregated_data.groupby("Artist"):
        # Extract stream, video, audio counts into a list and clean data
        stream_counts = (
            group["This Period Streams"].fillna("0").astype(int).tolist()[::-1]
        )
        audio_counts = (
            group["Audio Streams This Period"].fillna("0").astype(int).tolist()[::-1]
        )
        video_counts = (
            group["Video Streams This Period"].fillna("0").astype(int).tolist()[::-1]
        )

        # Calculate total streams for the specified periods
        tp_total_streams = sum(stream_counts[7:12])
        lp_total_streams = sum(stream_counts[0:7])
        tp_audio_streams = sum(audio_counts[7:12])
        tp_video_streams = sum(video_counts[7:12])
        # Avoid division by zero
        if tp_total_streams == 0:
            audio_percent_change = np.nan
            video_percent_change = np.nan
        else:
            audio_percent_change = (tp_audio_streams / tp_total_streams) * 100
            video_percent_change = (tp_video_streams / tp_total_streams) * 100

        # Avoid division by zero
        if lp_total_streams == 0:
            percent_change = np.nan  # or use 0 or any other placeholder
        else:
            percent_change = (
                (tp_total_streams - lp_total_streams) / lp_total_streams * 100
            )

        # Construct the date range string
        date_range = f"{group['Rolling Date Range'].min().strftime('%A, %d %b %Y')} - {group['Rolling Date Range'].max().strftime('%A, %d %b %Y')}"

        # Create a temporary DataFrame and concat it with result_df
        temp_df = pd.DataFrame(
            {
                "Artist": [artist],
                "Date Range": [date_range],
                "TP Total Streams (Days 8 - 12)": [tp_total_streams],
                "LP Total Streams (Days 1 - 7)": [lp_total_streams],
                "% Change (LP to TP)": [percent_change],
                "TP Audio Streams": [tp_audio_streams],
                "Audio %": [audio_percent_change],
                "TP Video Streams": [tp_video_streams],
                "Video %": [video_percent_change],
                "Stream Counts": [stream_counts],
            }
        )
        result_df = pd.concat([result_df, temp_df], ignore_index=True)

    # Remove date range column
    result_df.drop(columns=["Date Range"], inplace=True)
    period_min = aggregated_data["Rolling Date Range"].min().strftime("%A, %d %b %Y")
    period_max = aggregated_data["Rolling Date Range"].max().strftime("%A, %d %b %Y")

    if len(all_data) == 1:
        st.markdown(
            f"***Report for :violet[{len(all_data)}] file ({period_min} - {period_max})***"
        )
    elif len(all_data) > 1:
        st.markdown(
            f"***Report for :violet[{len(all_data)}] files ({period_min} - {period_max})***"
        )

    st.dataframe(
        result_df,
        use_container_width=True,
        hide_index=True,
        column_config={"Stream Counts": st.column_config.AreaChartColumn()},
    )
