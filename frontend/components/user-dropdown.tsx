"use client"

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { User, Settings, HelpCircle, LogOut } from "lucide-react"
import { useAuth } from "@/hooks/useAuth"
import { useRouter } from "next/navigation"

interface UserDropdownProps {
  userName?: string
  userEmail?: string
  userAvatar?: string
}

export function UserDropdown({
  userName,
  userEmail,
  userAvatar,
}: UserDropdownProps) {
  const { user, logout } = useAuth();
  const router = useRouter();
  
  // Sử dụng thông tin từ props hoặc từ context auth
  const displayName = userName || user?.name || user?.email?.split('@')[0] || "User";
  const displayEmail = userEmail || user?.email || "";
  const displayAvatar = userAvatar || user?.avatar_url || "";

  // Lấy chữ cái đầu tiên của tên người dùng
  const initials = displayName
    .split(" ")
    .map((name) => name[0])
    .join("")
    .toUpperCase()
    .substring(0, 2)

  const handleLogout = async () => {
    await logout();
    router.push("/auth/login");
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Avatar className="h-8 w-8 cursor-pointer">
          {displayAvatar ? (
            <AvatarImage src={displayAvatar} alt={displayName} />
          ) : (
            <AvatarFallback className="bg-primary text-primary-foreground">{initials}</AvatarFallback>
          )}
        </Avatar>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-56" align="end" forceMount>
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium leading-none">{displayName}</p>
            <p className="text-xs leading-none text-muted-foreground truncate">{displayEmail}</p>
          </div>
        </DropdownMenuLabel>
        {/* <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuItem>
            <User className="mr-2 h-4 w-4" />
            <span>Hồ sơ</span>
          </DropdownMenuItem>
          <DropdownMenuItem>
            <Settings className="mr-2 h-4 w-4" />
            <span>Cài đặt</span>
          </DropdownMenuItem>
          <DropdownMenuItem>
            <HelpCircle className="mr-2 h-4 w-4" />
            <span>Trợ giúp</span>
          </DropdownMenuItem>
        </DropdownMenuGroup>
        <DropdownMenuSeparator /> */}
        <DropdownMenuItem 
          className="text-destructive focus:text-destructive cursor-pointer" 
          onClick={handleLogout}
        >
          <LogOut className="mr-2 h-4 w-4" />
          <span>Đăng xuất</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
