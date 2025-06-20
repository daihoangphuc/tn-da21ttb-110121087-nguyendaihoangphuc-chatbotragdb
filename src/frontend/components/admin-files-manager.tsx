"use client";

import { useState, useEffect, useRef } from "react";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { toast } from "@/components/ui/use-toast";
import { 
  Upload, 
  Trash2, 
  FileText,
  File,
  RefreshCw,
  Search,
  MoreHorizontal
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { fetchApi } from "@/lib/api";

// Types for File Management
interface FileInfo {
  id: string;
  filename: string;
  path: string;
  size: number;
  upload_date: string;
  extension: string;
  category?: string;
}

interface FileListResponse {
  total_files: number;
  files: FileInfo[];
}

interface UploadResponse {
  filename: string;
  status: string;
  message: string;
  chunks_count?: number;
  category?: string;
  file_id?: string;
  shared_resource?: boolean;
}

interface DeleteResponse {
  filename: string;
  status: string;
  message: string;
  removed_points?: number;
}

export function AdminFilesManager() {
  const { user } = useAuth();
  
  // State
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [totalFiles, setTotalFiles] = useState(0);
  const [searchTerm, setSearchTerm] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  
  // Upload states
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadCategory, setUploadCategory] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch files function
  const fetchFiles = async () => {
    try {
      setLoading(true);
      const data: FileListResponse = await fetchApi('/files');
      setFiles(data.files || []);
      setTotalFiles(data.total_files || 0);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Lỗi",
        description: "Không thể tải danh sách file"
      });
    } finally {
      setLoading(false);
    }
  };

  // Upload file function
  const uploadFile = async () => {
    if (!selectedFile) {
      toast({
        variant: "destructive",
        title: "Lỗi",
        description: "Vui lòng chọn file để upload"
      });
      return;
    }

    try {
      setUploading(true);
      setUploadProgress(0);

      const formData = new FormData();
      formData.append('file', selectedFile);
      if (uploadCategory) {
        formData.append('category', uploadCategory);
      }

      // Simulate progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return prev;
          }
          return prev + 10;
        });
      }, 200);

      // Get auth token (try both sources)
      let token = localStorage.getItem('auth_token');
      if (!token) {
        const session = localStorage.getItem('session');
        if (session) {
          try {
            const sessionData = JSON.parse(session);
            token = sessionData.access_token;
          } catch (e) {
            console.error('Error parsing session data:', e);
          }
        }
      }

      // Use the same API base URL as fetchApi
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://34.30.191.213:8000/api';
      const url = `${API_BASE_URL}/upload`;
      
      console.log('Uploading to URL:', url);
      console.log('Has token:', !!token);
      console.log('File:', selectedFile.name, 'Size:', selectedFile.size);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          // Don't set Content-Type for FormData - browser will set it automatically
        },
        body: formData
      });

      clearInterval(progressInterval);
      setUploadProgress(100);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Upload failed: ${response.status} ${response.statusText}: ${errorText}`);
      }

      const result: UploadResponse = await response.json();

      toast({
        title: "Thành công",
        description: result.message
      });

      setShowUploadModal(false);
      setSelectedFile(null);
      setUploadCategory("");
      fetchFiles();
    } catch (error) {
      console.error('Upload error:', error);
      toast({
        variant: "destructive",
        title: "Lỗi",
        description: error instanceof Error ? error.message : "Không thể upload file"
      });
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  // Delete file function
  const deleteFile = async (filename: string) => {
    if (!confirm(`Bạn có chắc chắn muốn xóa file "${filename}"?`)) return;
    
    try {
      setLoading(true);
      const response: DeleteResponse = await fetchApi(`/files/${encodeURIComponent(filename)}`, {
        method: 'DELETE'
      });

      toast({
        title: "Thành công",
        description: response.message
      });

      fetchFiles();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Lỗi",
        description: "Không thể xóa file"
      });
    } finally {
      setLoading(false);
    }
  };

  // Handle file selection
  const handleFileSelection = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Check file type
      const allowedTypes = ['.pdf', '.docx', '.txt', '.md', '.sql'];
      const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
      
      if (!allowedTypes.includes(fileExtension)) {
        toast({
          variant: "destructive",
          title: "Lỗi",
          description: `Chỉ hỗ trợ các định dạng: ${allowedTypes.join(', ')}`
        });
        return;
      }

      // Check file size (10MB limit)
      if (file.size > 10 * 1024 * 1024) {
        toast({
          variant: "destructive",
          title: "Lỗi",
          description: "File không được lớn hơn 10MB"
        });
        return;
      }

      setSelectedFile(file);
    }
  };

  // Effects
  useEffect(() => {
    fetchFiles();
  }, []);

  // Helper functions
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString("vi-VN");
  };

  const getFileIcon = (extension: string) => {
    switch (extension.toLowerCase()) {
      case '.pdf':
        return <FileText className="w-4 h-4 text-red-500" />;
      case '.docx':
        return <FileText className="w-4 h-4 text-blue-500" />;
      case '.txt':
      case '.md':
        return <File className="w-4 h-4 text-gray-500" />;
      case '.sql':
        return <File className="w-4 h-4 text-green-500" />;
      default:
        return <File className="w-4 h-4 text-gray-400" />;
    }
  };

  const getCategoryBadge = (category?: string) => {
    if (!category) return null;
    return <Badge variant="secondary">{category}</Badge>;
  };

  // Filter files
  const filteredFiles = files.filter(file => {
    const matchesSearch = file.filename.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = !categoryFilter || categoryFilter === "all" || file.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  // Get unique categories
  const categories = Array.from(new Set(files.map(f => f.category).filter(Boolean)));

  return (
    <div className="space-y-6 relative">
      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 bg-background/80 backdrop-blur-sm z-10 flex items-center justify-center">
          <div className="flex flex-col items-center space-y-2">
            <Upload className="h-8 w-8 animate-bounce text-primary" />
            <p className="text-sm text-muted-foreground">Đang xử lý...</p>
          </div>
        </div>
      )}
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Tổng file</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalFiles}</div>
            <p className="text-xs text-muted-foreground">Đã upload</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">PDF</CardTitle>
            <FileText className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {files.filter(f => f.extension === '.pdf').length}
            </div>
            <p className="text-xs text-muted-foreground">Tài liệu PDF</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">DOCX</CardTitle>
            <FileText className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {files.filter(f => f.extension === '.docx').length}
            </div>
            <p className="text-xs text-muted-foreground">Tài liệu Word</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Khác</CardTitle>
            <File className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {files.filter(f => !['.pdf', '.docx'].includes(f.extension)).length}
            </div>
            <p className="text-xs text-muted-foreground">TXT, MD, SQL</p>
          </CardContent>
        </Card>
      </div>

      {/* Files Management */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle>Quản lý tài liệu</CardTitle>
              <CardDescription>
                Upload và quản lý tài liệu hệ thống
              </CardDescription>
            </div>
            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={fetchFiles}
                className="flex items-center gap-2"
                disabled={loading}
              >
                <RefreshCw className="w-4 h-4" />
                {loading ? "Đang tải..." : "Làm mới"}
              </Button>
              <Dialog open={showUploadModal} onOpenChange={setShowUploadModal}>
                <DialogTrigger asChild>
                  <Button className="flex items-center gap-2">
                    <Upload className="w-4 h-4" />
                    Upload tài liệu
                  </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-[500px]">
                  <DialogHeader>
                    <DialogTitle>Upload tài liệu mới</DialogTitle>
                    <DialogDescription>
                      Chọn tài liệu để upload vào hệ thống. Hỗ trợ PDF, DOCX, TXT, MD, SQL (tối đa 10MB).
                    </DialogDescription>
                  </DialogHeader>
                  <div className="grid gap-4 py-4">
                    <div className="space-y-2">
                      <Label htmlFor="file">Chọn file</Label>
                      <Input
                        id="file"
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileSelection}
                        accept=".pdf,.docx,.txt,.md,.sql"
                        disabled={uploading}
                      />
                      {selectedFile && (
                        <div className="text-sm text-gray-600">
                          <p>File đã chọn: {selectedFile.name}</p>
                          <p>Kích thước: {formatFileSize(selectedFile.size)}</p>
                        </div>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="category">Danh mục (tùy chọn)</Label>
                      <Input
                        id="category"
                        value={uploadCategory}
                        onChange={(e) => setUploadCategory(e.target.value)}
                        placeholder="Ví dụ: Cơ sở dữ liệu, SQL..."
                        disabled={uploading}
                      />
                    </div>
                    {uploading && (
                      <div className="space-y-2">
                        <Label>Tiến trình upload</Label>
                        <Progress value={uploadProgress} className="w-full" />
                        <p className="text-sm text-gray-600">{uploadProgress}%</p>
                      </div>
                    )}
                  </div>
                  <DialogFooter>
                    <Button 
                      type="submit" 
                      onClick={uploadFile}
                      disabled={!selectedFile || uploading}
                    >
                      {uploading ? "Đang upload..." : "Upload"}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          <div className="flex items-center space-x-4 mb-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Tìm kiếm file..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-8"
              />
            </div>
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Lọc theo danh mục" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tất cả danh mục</SelectItem>
                {categories.map((category) => (
                  <SelectItem key={category} value={category}>
                    {category}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Files Table */}
          {loading ? (
            <div className="space-y-4">
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="flex items-center space-x-4 p-4 border rounded">
                    <Skeleton className="h-4 w-4" />
                    <Skeleton className="h-4 w-48" />
                    <Skeleton className="h-4 w-20" />
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-8 w-8 rounded" />
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>File</TableHead>
                  <TableHead>Kích thước</TableHead>
                  <TableHead>Danh mục</TableHead>
                  <TableHead>Ngày upload</TableHead>
                  <TableHead className="text-right">Hành động</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredFiles.length > 0 ? (
                  filteredFiles.map((file) => (
                    <TableRow key={file.id}>
                      <TableCell>
                        <div className="flex items-center space-x-2">
                          {getFileIcon(file.extension)}
                          <span className="font-medium">{file.filename}</span>
                        </div>
                      </TableCell>
                      <TableCell>{formatFileSize(file.size)}</TableCell>
                      <TableCell>{getCategoryBadge(file.category)}</TableCell>
                      <TableCell>{formatDate(file.upload_date)}</TableCell>
                      <TableCell className="text-right">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" className="h-8 w-8 p-0" disabled={loading}>
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem
                              onClick={() => deleteFile(file.filename)}
                              className="text-red-600"
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              Xóa
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-8">
                      {searchTerm || (categoryFilter && categoryFilter !== "all") ? "Không tìm thấy file phù hợp" : "Chưa có file nào được upload"}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
} 