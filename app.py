elif page == "1. Customer Registration":
        st.title("📋 Customer Registration & Management")
        
        # Clear inputs at the top before widgets are instantiated
        if st.session_state.get("clear_form_flag", False):
            st.session_state["cust_name_input"] = ""
            st.session_state["cust_phone_input"] = ""
            st.session_state["eng_name_input"] = ""
            st.session_state["eng_mob_input"] = ""
            st.session_state["cust_addr_input"] = ""
            st.session_state["clear_form_flag"] = False

        cust_name = st.text_input("Customer Name", key="cust_name_input")
        cust_phone = st.text_input("Phone Number", key="cust_phone_input")
        engineer_name = st.text_input("Engineer Name", key="eng_name_input")
        engineer_mobile = st.text_input("Engineer Mobile", key="eng_mob_input")
        cust_address = st.text_area("Address", key="cust_addr_input")
        
        if st.button("Save Customer to Supabase"):
            if cust_name and cust_phone:
                cust_data = {
                    "name": cust_name,
                    "mobile": cust_phone,
                    "phone": cust_phone,
                    "engineer": engineer_name,
                    "engineer_mobile": engineer_mobile,
                    "address": cust_address,
                    "branch": branch_name
                }
                success = save_customer_to_db(cust_data)
                if success:
                    st.success(f"Customer {cust_name} saved successfully!")
                    st.session_state["clear_form_flag"] = True
                    st.rerun()
                else:
                    st.error("Failed to save customer to database.")
            else:
                st.error("Please enter Customer Name and Phone number.")
                
        st.markdown("### Existing Customers (Supabase Database)")
        customers = get_all_customers()
        if customers:
            for idx, c in enumerate(customers):
                c_id = c.get('id', str(idx))
                c_phone = c.get('phone', '') or c.get('mobile', 'no_phone')
                col1, col2, col3 = st.columns([3, 2, 2])
                with col1:
                    st.write(f"**{c.get('name')}** | Mobile: {c_phone} | Addr: {c.get('address', '')}")
                with col2:
                    if st.button("Select for Tiles", key=f"select_cust_{c_id}_{idx}"):
                        st.session_state["selected_customer"] = c
                        st.success(f"Selected customer: {c.get('name')}. Switch to 'Area-wise Tile Selection'.")
                with col3:
                    if st.button("Delete", key=f"del_cust_{c_id}_{idx}"):
                        delete_customer_from_db(c_id)
                        st.success(f"Customer {c.get('name')} deleted successfully!")
                        st.rerun()
        else:
            st.info("No customers found in database.")
