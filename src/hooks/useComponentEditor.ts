/**
 * useComponentEditor - 管理 Component 和 Config 编辑状态
 */

import { useState, useCallback } from 'react';
import type { PromptComponent } from '@/types';

interface EditedComponent {
  id: string;
  content: string | null;
  content_json: any;
}

interface RequestConfig {
  endpoint?: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  top_k?: number;
}

export function useComponentEditor() {
  // 存储被编辑的 components，key 是 component.id
  const [editedComponents, setEditedComponents] = useState<Map<string, EditedComponent>>(
    new Map()
  );

  // 存储被编辑的请求配置
  const [editedConfig, setEditedConfig] = useState<RequestConfig>({});

  // 获取 component 的当前值（编辑后的或原始的）
  const getComponentValue = useCallback(
    (component: PromptComponent): { content: string | null; content_json: any } => {
      const edited = editedComponents.get(component.id);
      if (edited) {
        return { content: edited.content, content_json: edited.content_json };
      }
      return { content: component.content, content_json: component.content_json };
    },
    [editedComponents]
  );

  // 保存编辑
  const saveEdit = useCallback((componentId: string, content: string | null, content_json: any) => {
    setEditedComponents((prev) => {
      const next = new Map(prev);
      next.set(componentId, { id: componentId, content, content_json });
      return next;
    });
  }, []);

  // 取消编辑
  const cancelEdit = useCallback((componentId: string) => {
    setEditedComponents((prev) => {
      const next = new Map(prev);
      next.delete(componentId);
      return next;
    });
  }, []);

  // 重置所有编辑
  const resetAll = useCallback(() => {
    setEditedComponents(new Map());
    setEditedConfig({});
  }, []);

  // 检查是否有编辑
  const isEdited = useCallback((componentId: string) => {
    return editedComponents.has(componentId);
  }, [editedComponents]);

  // 获取所有编辑
  const getAllEdits = useCallback(() => {
    return Array.from(editedComponents.values());
  }, [editedComponents]);

  // 配置编辑方法
  const updateConfig = useCallback((key: keyof RequestConfig, value: any) => {
    setEditedConfig((prev) => ({
      ...prev,
      [key]: value,
    }));
  }, []);

  const getConfigValue = useCallback((key: keyof RequestConfig, defaultValue: any) => {
    return editedConfig[key] !== undefined ? editedConfig[key] : defaultValue;
  }, [editedConfig]);

  const hasConfigEdits = Object.keys(editedConfig).length > 0;

  // 是否有任何编辑
  const hasAnyEdits = editedComponents.size > 0 || hasConfigEdits;

  return {
    getComponentValue,
    saveEdit,
    cancelEdit,
    resetAll,
    isEdited,
    getAllEdits,
    hasAnyEdits,
    // 配置编辑
    updateConfig,
    getConfigValue,
    editedConfig,
    hasConfigEdits,
  };
}
