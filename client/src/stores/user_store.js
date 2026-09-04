import { defineStore } from "pinia"
import { onBeforeMount, ref } from "vue"
import axios from "axios"

export const useUserStore = defineStore("userStore", () => {
    const userInfo = ref({
        is_authenticated: false,
    })

    async function checkLogin() {
        try {
            let r = await axios.get("/api/user/info/")
            userInfo.value = r.data
        } catch (error) {
            userInfo.value = {
                is_authenticated: false,
            }
        }
    }

    async function login(username, password) {
        await axios.post("/api/user/login/", {
            username: username,
            password: password,
        })
        await checkLogin()
    }

    async function logout() {
        try {
            await axios.post("/api/user/logout/")
        } catch (error) {
            console.error("Logout error:", error)
        } finally {
            userInfo.value = {
                is_authenticated: false,
            }
        }
    }

    onBeforeMount(async () => {
        await checkLogin()
    })

    return {
        userInfo,
        checkLogin,
        login,
        logout,
    }
})
