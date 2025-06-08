"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Checkbox } from "@/components/ui/checkbox"
import { FileUp, FileIcon, File, FileText, FileCode, Upload, X, Plus } from "lucide-react"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { filesApi, uploadApi } from "@/lib/api"
import { useToast } from "@/components/ui/use-toast"

// Định nghĩa kiểu dữ liệu cho tài liệu
interface FileDocument {
  id: string;
  name: string;
  progress: number;
  complete: boolean;
  selected: boolean;
  file_id?: string;
  category?: string | null;
  chunks_count?: number;
  upload_date?: string;
}

// Định nghĩa kiểu dữ liệu cho file từ API
interface FileResponse {
  id?: string;
  file_id?: string;
  filename: string;
  path?: string;
  size?: number;
  upload_date?: string;
  extension?: string;
  category?: string | null;
  chunks_count?: number;
}

// Hàm tiện ích để lấy biểu tượng file dựa vào định dạng
const getFileIcon = (filename: string) => {
  const extension = filename.split('.').pop()?.toLowerCase();
  
  switch(extension) {
    case 'pdf':
      return <FileIcon className="h-8 w-8 text-red-500 flex-shrink-0" />;
    case 'docx':
    case 'doc':
      return <FileText className="h-8 w-8 text-blue-500 flex-shrink-0" />;
    case 'txt':
      return <FileText className="h-8 w-8 text-gray-500 flex-shrink-0" />;
    case 'sql':
      return <FileCode className="h-8 w-8 text-amber-500 flex-shrink-0" />;
    default:
      return <File className="h-8 w-8 text-primary/80 flex-shrink-0" />;
  }
};

interface FileUploaderProps {
  onSelectedFilesChange?: (selectedIds: string[]) => void;
}

export function FileUploader({ onSelectedFilesChange }: FileUploaderProps) {
  const [files, setFiles] = useState<FileDocument[]>([])
  const [uploading, setUploading] = useState(false)
  const [fileToDelete, setFileToDelete] = useState<string | null>(null)
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false)
  const [selectAll, setSelectAll] = useState(false)
  const [loading, setLoading] = useState(true)
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropAreaRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  // Tải danh sách tài liệu khi component mount
  useEffect(() => {
    const fetchFiles = async () => {
      try {
        setLoading(true);
        const response = await filesApi.getFiles();
        console.log('API response:', response);
        
        // Kiểm tra cấu trúc response
        let filesList: FileResponse[] = [];
        if (response && response.files && Array.isArray(response.files)) {
          // Trường hợp API trả về dạng { total_files, files: [] }
          filesList = response.files;
        } else if (response && Array.isArray(response)) {
          // Trường hợp API trả về trực tiếp mảng
          filesList = response;
        } else {
          console.error('Cấu trúc dữ liệu không hợp lệ:', response);
          setFiles([]);
          return;
        }
        
        const formattedFiles = filesList.map((file: FileResponse) => ({
          id: file.id || file.file_id || file.filename,
          name: file.filename,
          progress: 100,
          complete: true,
          selected: false,
          file_id: file.id || file.file_id,
          category: file.category,
          chunks_count: file.chunks_count,
          upload_date: file.upload_date
        }));
        
        console.log('Formatted files:', formattedFiles);
        setFiles(formattedFiles);
      } catch (error) {
        console.error('Lỗi khi tải danh sách tài liệu:', error);
        toast({
          variant: "destructive",
          title: "Lỗi",
          description: "Không thể tải danh sách tài liệu. Vui lòng thử lại sau."
        });
      } finally {
        setLoading(false);
      }
    };
    
    fetchFiles();
  }, [toast]);

  const handleToggleSelect = (id: string, e?: React.MouseEvent) => {
    e?.stopPropagation()
    const updatedFiles = files.map((file) => (file.id === id ? { ...file, selected: !file.selected } : file));
    setFiles(updatedFiles);
    
    // Kiểm tra xem sau khi thay đổi trạng thái của file này, tất cả file có được chọn không
    const allSelected = updatedFiles.every(file => file.selected);
    setSelectAll(allSelected);

    // Thông báo cho component cha về các file được chọn
    const selectedIds = updatedFiles.filter(file => file.selected).map(file => file.file_id || file.id);
    onSelectedFilesChange?.(selectedIds);
  }

  const handleSelectAll = (checked: boolean) => {
    const updatedFiles = files.map(file => ({ ...file, selected: checked }));
    setFiles(updatedFiles);
    setSelectAll(checked);

    // Thông báo cho component cha về các file được chọn
    const selectedIds = checked ? updatedFiles.map(file => file.file_id || file.id) : [];
    onSelectedFilesChange?.(selectedIds);
  }

  const handleDeleteClick = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setFileToDelete(id)
  }

  const handleConfirmDelete = async () => {
    if (fileToDelete) {
      try {
        const fileToRemove = files.find(file => file.id === fileToDelete);
        if (!fileToRemove) return;
        await filesApi.deleteFile(fileToRemove.name);
        setFiles(files.filter((file) => file.id !== fileToDelete));
        toast({
          title: "Xóa thành công",
          description: `Đã xóa tài liệu ${fileToRemove.name}`
        });
      } catch (error: any) {
        // Nếu lỗi 404 (file không tồn tại), vẫn xóa khỏi giao diện và báo cho user
        if (error.message && (error.message.includes("không tồn tại") || error.message.includes("404"))) {
          setFiles(files.filter((file) => file.id !== fileToDelete));
          toast({
            title: "Đã xóa khỏi danh sách",
            description: "File đã bị xóa hoặc không tồn tại trên server."
          });
        } else {
          toast({
            variant: "destructive",
            title: "Lỗi",
            description: error.message || "Không thể xóa tài liệu. Vui lòng thử lại sau."
          });
        }
      } finally {
        setFileToDelete(null);
        // Cập nhật lại trạng thái selectAll sau khi xóa
        const remainingFiles = files.filter((file) => file.id !== fileToDelete);
        setSelectAll(remainingFiles.length > 0 && remainingFiles.every(file => file.selected));
      }
    }
  }

  const handleFileSelect = () => {
    // Kích hoạt input file khi nhấn vào button
    fileInputRef.current?.click();
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files;
    if (!selectedFiles || selectedFiles.length === 0) return;
    
    setUploading(true);
    
    for (const file of Array.from(selectedFiles)) {
      try {
        // Thêm file vào danh sách với trạng thái đang tải
        const tempId = Date.now() + Math.random().toString();
        const newFile: FileDocument = {
          id: tempId,
          name: file.name,
          progress: 0,
          complete: false,
          selected: false
        };
        
        setFiles(prev => [...prev, newFile]);
        
        // Tải file lên server
        const response = await uploadApi.uploadFile(file);
        
        if (response && response.status === "success") {
          // Cập nhật trạng thái file sau khi tải lên thành công
          setFiles(prev => prev.map(f => 
            f.id === tempId ? {
              ...f,
              id: response.file_id || tempId,
              file_id: response.file_id,
              name: response.filename || f.name,
              progress: 100,
              complete: true,
              chunks_count: response.chunks_count,
              category: response.category
            } : f
          ));
          
          toast({
            title: "Tải lên thành công",
            description: response.message || `Đã tải lên tài liệu ${file.name}`
          });
        } else {
          // Xóa file khỏi danh sách nếu tải lên thất bại
          setFiles(prev => prev.filter(f => f.id !== tempId));
          
          toast({
            variant: "destructive",
            title: "Lỗi",
            description: response.message || `Không thể tải lên tài liệu ${file.name}`
          });
        }
      } catch (error: any) {
        console.error('Lỗi khi tải lên tài liệu:', error);
        toast({
          variant: "destructive",
          title: "Lỗi",
          description: error.message || `Không thể tải lên tài liệu ${file.name}`
        });
      }
    }
    
    setUploading(false);
    
    // Reset input để có thể chọn lại cùng một file
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    
    // Đóng dialog sau khi tải lên
    setUploadDialogOpen(false);
    
    // Cập nhật lại trạng thái selectAll
    setSelectAll(false);
  }

  // Xử lý sự kiện kéo thả file
  const handleDragEnter = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isDragging) {
      setIsDragging(true);
    }
  };

  const handleDrop = async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    const files = e.dataTransfer.files;
    if (!files || files.length === 0) return;
    
    setUploading(true);
    
    for (const file of Array.from(files)) {
      try {
        // Kiểm tra định dạng file
        const extension = file.name.split('.').pop()?.toLowerCase();
        const allowedExtensions = ['pdf', 'docx', 'doc', 'txt', 'sql'];
        
        if (!extension || !allowedExtensions.includes(extension)) {
          toast({
            variant: "destructive",
            title: "Định dạng không hỗ trợ",
            description: `Định dạng ${extension} không được hỗ trợ. Vui lòng tải lên file PDF, DOCX, TXT hoặc SQL.`
          });
          continue;
        }
        
        // Thêm file vào danh sách với trạng thái đang tải
        const tempId = Date.now() + Math.random().toString();
        const newFile: FileDocument = {
          id: tempId,
          name: file.name,
          progress: 0,
          complete: false,
          selected: false
        };
        
        setFiles(prev => [...prev, newFile]);
        
        // Tải file lên server
        const response = await uploadApi.uploadFile(file);
        
        if (response && response.status === "success") {
          // Cập nhật trạng thái file sau khi tải lên thành công
          setFiles(prev => prev.map(f => 
            f.id === tempId ? {
              ...f,
              id: response.file_id || tempId,
              file_id: response.file_id,
              name: response.filename || f.name,
              progress: 100,
              complete: true,
              chunks_count: response.chunks_count,
              category: response.category
            } : f
          ));
          
          toast({
            title: "Tải lên thành công",
            description: response.message || `Đã tải lên tài liệu ${file.name}`
          });
        } else {
          // Xóa file khỏi danh sách nếu tải lên thất bại
          setFiles(prev => prev.filter(f => f.id !== tempId));
          
          toast({
            variant: "destructive",
            title: "Lỗi",
            description: response.message || `Không thể tải lên tài liệu ${file.name}`
          });
        }
      } catch (error: any) {
        console.error('Lỗi khi tải lên tài liệu:', error);
        toast({
          variant: "destructive",
          title: "Lỗi",
          description: error.message || `Không thể tải lên tài liệu ${file.name}`
        });
      }
    }
    
    setUploading(false);
    
    // Đóng dialog sau khi tải lên
    setUploadDialogOpen(false);
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          <h4 className="text-sm font-medium">Nguồn</h4>
          <div className="flex items-center space-x-2">
            <Checkbox 
              id="select-all-sources" 
              checked={selectAll}
              onCheckedChange={(checked) => handleSelectAll(checked === true)}
            />
            <label
              htmlFor="select-all-sources"
              className="text-xs text-muted-foreground cursor-pointer"
            >
              Chọn mọi nguồn
            </label>
          </div>
        </div>
        <Button 
          variant="outline" 
          size="default" 
          className="gap-1 px-4"
          onClick={() => setUploadDialogOpen(true)}
        >
          <Plus className="h-4 w-4" />
          Thêm
        </Button>
      </div>

      <div className="space-y-2">
        <div className="max-w-full overflow-hidden">
          {loading ? (
            <div className="flex justify-center items-center py-8">
              <div className="w-8 h-8 border-t-2 border-b-2 border-primary rounded-full animate-spin"></div>
            </div>
          ) : files.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-sm">Chưa có tài liệu nào được tải lên</div>
          ) : (
            files.map((file) => (
              <Card key={file.id} className="overflow-hidden mb-2 max-w-full">
                <CardContent className="p-3 cursor-pointer" onClick={() => handleToggleSelect(file.id)}>
                  <div className="flex items-center gap-3">
                    <Checkbox
                      checked={file.selected}
                      onCheckedChange={() => handleToggleSelect(file.id)}
                      className="data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground"
                      onClick={(e) => e.stopPropagation()}
                    />
                    {getFileIcon(file.name)}
                    <div className="grid flex-1 gap-1 min-w-0 max-w-full overflow-hidden">
                      <div className="flex items-center justify-between">
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span className="text-sm font-medium truncate max-w-[120px] block">{file.name}</span>
                            </TooltipTrigger>
                            <TooltipContent side="top">
                              <p>{file.name}</p>
                              {file.chunks_count && <p className="text-xs text-muted-foreground">{file.chunks_count} chunks</p>}
                              {file.category && <p className="text-xs text-muted-foreground">Danh mục: {file.category}</p>}
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                        <div className="flex items-center gap-1 flex-shrink-0">
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-7 w-7 ml-1 text-destructive hover:text-destructive/90 hover:bg-destructive/10"
                                  onClick={(e) => handleDeleteClick(file.id, e)}
                                >
                                  <X className="h-4 w-4" />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>
                                <p>Xóa tài liệu</p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        </div>
                      </div>
                      <Progress value={file.progress} className="h-1" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </div>

      {/* Modal tải lên file */}
      <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Tải lên tài liệu</DialogTitle>
            <DialogDescription>
              Chọn tài liệu từ máy tính của bạn để tải lên hệ thống
            </DialogDescription>
          </DialogHeader>
          <div 
            className={`flex flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center transition-colors ${isDragging ? 'bg-primary/5 border-primary' : ''}`}
            onDragEnter={handleDragEnter}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            ref={dropAreaRef}
          >
            <div className="mb-4 rounded-full bg-primary/10 p-3">
              <FileUp className="h-6 w-6 text-primary" />
            </div>
            <h3 className="mb-1 text-lg font-semibold">Kéo thả hoặc tải lên tài liệu</h3>
            <p className="mb-4 text-sm text-muted-foreground">Hỗ trợ PDF, DOCX, TXT và SQL</p>
            <input 
              type="file" 
              ref={fileInputRef} 
              onChange={handleFileChange} 
              className="hidden" 
              multiple 
              accept=".pdf,.docx,.doc,.txt,.sql" 
            />
            <Button 
              size="sm" 
              onClick={handleFileSelect}
              disabled={uploading}
            >
              {uploading ? (
                <>
                  <div className="w-4 h-4 border-t-2 border-b-2 border-background rounded-full animate-spin mr-2"></div>
                  Đang tải lên...
                </>
              ) : (
                "Chọn tài liệu"
              )}
            </Button>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setUploadDialogOpen(false)} disabled={uploading}>Hủy</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal xác nhận xóa một file */}
      <AlertDialog open={!!fileToDelete} onOpenChange={(open) => !open && setFileToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Xác nhận xóa</AlertDialogTitle>
            <AlertDialogDescription>
              Bạn có chắc chắn muốn xóa tài liệu này? Hành động này không thể hoàn tác.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setFileToDelete(null)}>Hủy</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmDelete} className="bg-destructive text-destructive-foreground">
              Xóa
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
