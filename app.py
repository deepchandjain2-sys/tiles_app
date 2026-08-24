st.subheader("📁 Upload Master (CSV / Excel)")
    uploaded_file = st.file_uploader(
        "Upload Item Master File",
        type=["csv", "xlsx", "xls"],
        key="master_uploader",
    )

    default_master_path = "ITEM MASTER.csv"
    df = None

    if uploaded_file is not None:
      df = load_stock_from_upload(uploaded_file)
      if df is not None:
        st.success(f"Successfully loaded {len(df)} items from uploaded file!")
    elif os.path.exists(default_master_path):
      try:
        df = load_stock_from_upload(default_master_path)
        if df is not None:
          st.info(f"Auto-loaded {len(df)} items from default master file!")
      except Exception as e:
        st.error(f"Error reading default master file: {e}")
    else:
      st.warning("Please upload or ensure ITEM MASTER.csv is present.")
