import streamlit as st


class MistralKeyManager:
    def __init__(self, config):
        self.keys = config["keys"]
        self.mode = config["usage_mode"]
        if "mistral_key_pos" not in st.session_state:
            st.session_state.mistral_key_pos = 0

    def ordered_keys(self):
        if not self.keys: return []
        start = st.session_state.mistral_key_pos % len(self.keys)
        if self.mode == "round_robin":
            st.session_state.mistral_key_pos = (start + 1) % len(self.keys)
        return self.keys[start:] + self.keys[:start]

    def report_success(self, key_info):
        if self.mode == "sequential":
            st.session_state.mistral_key_pos = self.keys.index(key_info)

    def report_failure(self, key_info):
        if self.mode == "sequential":
            st.session_state.mistral_key_pos = (self.keys.index(key_info) + 1) % len(self.keys)
